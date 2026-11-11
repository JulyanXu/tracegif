"""Decode real GIF downloads from the self-contained offline HTML player."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/tracegif/scripts"))
from typebitlib.core import configure_project, prepare_project, render_project
from typebitlib.verify import external_resources


class BrowserGifTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            if os.environ.get("CI"):
                raise RuntimeError("CI must install Playwright.") from exc
            raise unittest.SkipTest("Playwright unavailable.") from exc
        cls.runtime = sync_playwright().start()
        try:
            cls.browser = cls.runtime.chromium.launch(headless=True)
        except Exception as exc:
            cls.runtime.stop()
            if os.environ.get("CI"):
                raise RuntimeError("CI must install Chromium.") from exc
            raise unittest.SkipTest("Chromium unavailable.") from exc

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.runtime.stop()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="typebit-browser-gif-")
        self.base = Path(self.temp.name)
        self.source = self.base / "source.svg"
        self.source.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 120">'
            '<rect id="body" x="30" y="25" width="100" height="70" rx="8" fill="#e67722"/>'
            '<circle id="window" cx="80" cy="60" r="13" fill="white"/>'
            '</svg>', encoding="utf-8")
        self.project = self.base / "project"
        prepare_project(self.source, self.project, duration=2)
        self.html = Path(render_project(self.project)["html"])
        self.unchanged = {name: (self.project / name).read_bytes()
                          for name in ("project.json", "scene.svg", "assets/source.svg")}
        self.context = self.browser.new_context(offline=True, accept_downloads=True,
                                                viewport={"width": 640, "height": 480})
        self.page = self.context.new_page()
        self.errors, self.requests, self.downloads = [], [], []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.on("request", lambda request: self.requests.append(request.url))
        self.page.on("download", lambda download: self.downloads.append(download))
        self.page.goto(self.html.as_uri())
        self.page.wait_for_function("Boolean(window.typebit)")

    def tearDown(self):
        self.assertEqual(self.errors, [])
        self.assertFalse(any(url.startswith(("http:", "https:")) for url in self.requests))
        self.context.close()
        self.temp.cleanup()

    def wait_finished(self):
        self.page.wait_for_function("!typebit.getState().exporting", timeout=15000)

    def assert_project_unchanged(self):
        for name, expected in self.unchanged.items():
            self.assertEqual((self.project / name).read_bytes(), expected, name)

    def download_gif(self, name="animation.gif"):
        with self.page.expect_download(timeout=15000) as pending:
            self.page.click("#typebit-download-gif")
        self.wait_finished()
        self.assertTrue(pending.value.suggested_filename.endswith(".gif"))
        target = self.base / name
        pending.value.save_as(target)
        return target

    def assert_gif(self, path, expected_ms):
        self.assertEqual(path.read_bytes()[:6], b"GIF89a")
        with Image.open(path) as image:
            self.assertEqual(image.format, "GIF")
            self.assertEqual(image.size, (160, 120))
            self.assertGreater(image.n_frames, 2)
            self.assertEqual(image.info.get("loop"), 0)
            frames, delays = [], []
            for index in range(image.n_frames):
                image.seek(index)
                frames.append(image.convert("RGB"))
                delays.append(image.info["duration"])
            self.assertEqual(sum(delays), expected_ms)
            self.assertGreaterEqual(delays[-1], 800)
            self.assertEqual(frames[0].getpixel((40, 40)), (255, 255, 255))
            final = frames[-1]
            self.assertEqual(final.getpixel((0, 0)), (255, 255, 255))
            self.assertEqual(final.getpixel((80, 60)), (255, 255, 255))
            for actual, expected in zip(final.getpixel((40, 40)), (230, 119, 34)):
                self.assertLessEqual(abs(actual - expected), 5)

    def test_gif_download_uses_selected_speed_real_frames_and_restores_pause(self):
        for rate, expected_ms in ((2, 1800), (4, 1300)):
            with self.subTest(rate=rate):
                self.page.evaluate("rate => {typebit.seek(.7);typebit.setPlaybackRate(rate)}", rate)
                before = self.page.evaluate("typebit.getState()")
                saved = self.download_gif(f"animation-{rate}.gif")
                self.assert_gif(saved, expected_ms)
                self.assertEqual(self.page.evaluate("typebit.getState()"), before)
                self.assert_project_unchanged()

    def test_custom_gif_settings_change_real_pixels_dimensions_and_frame_timing(self):
        self.page.locator("#typebit-gif-options").evaluate("element => element.open = true")
        self.page.select_option("#typebit-gif-width", "240")
        self.page.select_option("#typebit-gif-fps", "15")
        self.page.locator("#typebit-gif-background").fill("#10243a")
        self.page.evaluate("typebit.seek(.7)")
        before = self.page.evaluate("typebit.getState()")
        estimate = self.page.locator("#typebit-gif-estimate").inner_text()
        self.assertIn("240 × 180", estimate)
        self.assertIn("15 fps", estimate)
        self.assertIn("2.8 seconds", estimate)
        saved = self.download_gif("custom.gif")
        with Image.open(saved) as image:
            self.assertEqual(image.size, (240, 180))
            self.assertEqual(image.n_frames, 31)
            delays = []
            for index in range(image.n_frames):
                image.seek(index)
                delays.append(image.info["duration"])
            self.assertEqual(sum(delays), 2800)
            self.assertEqual(delays[-1], 800)
            self.assertEqual(set(delays[:-1]), {60, 70})
            final = image.convert("RGB")
            for actual, expected in zip(final.getpixel((0, 0)), (16, 36, 58)):
                self.assertLessEqual(abs(actual - expected), 2)
            self.assertEqual(final.getpixel((120, 90)), (255, 255, 255))
        self.assertEqual(self.page.evaluate("typebit.getState()"), before)
        self.assert_project_unchanged()

    def test_saved_html_retains_gif_preferences_and_the_new_public_api(self):
        self.assertTrue(self.page.evaluate("window.tracegif === window.typebit"))
        self.page.locator("#typebit-gif-options").evaluate("element => element.open = true")
        self.page.select_option("#typebit-gif-width", "240")
        self.page.select_option("#typebit-gif-fps", "5")
        self.page.locator("#typebit-gif-background").fill("#10243a")
        self.page.evaluate("tracegif.setPlaybackRate(2)")
        with self.page.expect_download() as pending:
            self.page.click("#typebit-download-html")
        saved = self.base / "custom-settings.html"
        pending.value.save_as(saved)
        self.page.goto(saved.as_uri())
        self.assertEqual(self.page.locator("#typebit-gif-width").input_value(), "240")
        self.assertEqual(self.page.locator("#typebit-gif-fps").input_value(), "5")
        self.assertEqual(self.page.locator("#typebit-gif-background").input_value(), "#10243a")
        self.assertEqual(self.page.evaluate("tracegif.getState().status"), "idle")
        self.assertEqual(self.page.evaluate("tracegif.getState().playbackRate"), 2)
        gif = self.download_gif("saved-settings.gif")
        with Image.open(gif) as image:
            self.assertEqual(image.size, (240, 180))
            self.assertEqual(image.n_frames, 6)
            self.assertEqual(image.convert("RGB").getpixel((0, 0)), (16, 36, 58))
        self.assert_project_unchanged()

    def test_cancel_restores_frame_and_does_not_download(self):
        for method in ("button", "escape"):
            with self.subTest(method=method):
                self.page.evaluate("typebit.seek(.6);typebit.setPlaybackRate(.25)")
                before = self.page.evaluate("typebit.getState()")
                self.page.click("#typebit-download-gif")
                self.page.wait_for_function("typebit.getState().exporting")
                for identity in ("typebit-gif-width", "typebit-gif-fps", "typebit-gif-background"):
                    self.assertTrue(self.page.locator(f"#{identity}").is_disabled())
                if method == "button":
                    self.page.click("#typebit-cancel-export")
                else:
                    self.page.keyboard.press("Escape")
                self.page.wait_for_function("document.getElementById('typebit-export-status').textContent === 'GIF export canceled.'")
                self.wait_finished()
                self.assertEqual(self.page.evaluate("typebit.getState()"), before)
                self.assertEqual(self.downloads, [])
                self.assertFalse(self.page.locator("#typebit-cancel-export").is_visible())
                self.assertTrue(self.page.locator("#typebit-download-gif").is_enabled())
                for identity in ("typebit-gif-width", "typebit-gif-fps", "typebit-gif-background"):
                    self.assertTrue(self.page.locator(f"#{identity}").is_enabled())
                self.assert_project_unchanged()

    def test_cancel_and_progress_remain_visible_in_a_short_window(self):
        self.page.set_viewport_size({"width": 790, "height": 240})
        self.page.locator("#typebit-gif-options").evaluate("element => element.open = true")
        self.page.evaluate("typebit.seek(.6);typebit.setPlaybackRate(.25)")
        before = self.page.evaluate("typebit.getState()")
        self.page.click("#typebit-download-gif")
        self.page.wait_for_function("typebit.getState().exporting")
        for identity in ("typebit-cancel-export", "typebit-export-status"):
            box = self.page.locator(f"#{identity}").bounding_box()
            self.assertGreaterEqual(box["y"], 0)
            self.assertLessEqual(box["y"] + box["height"], 240)
        self.page.click("#typebit-cancel-export")
        self.wait_finished()
        self.assertEqual(self.page.evaluate("typebit.getState()"), before)
        self.assertEqual(self.downloads, [])

    def test_export_resumes_prior_playing_position_instead_of_final_frame(self):
        self.page.evaluate("typebit.seek(.6);typebit.setPlaybackRate(1);typebit.play()")
        with self.page.expect_download(timeout=15000) as pending:
            before = self.page.evaluate("""() => {
                const before = typebit.getState();
                document.getElementById('typebit-download-gif').click();
                return before;
            }""")
        self.wait_finished()
        after = self.page.evaluate("const state=typebit.getState();typebit.pause();state")
        self.assertEqual(after["status"], "playing")
        self.assertGreaterEqual(after["time"], before["time"])
        self.assertLess(after["time"] - before["time"], .2)
        pending.value.save_as(self.base / "resumed.gif")
        self.assert_project_unchanged()

    def test_saved_html_contains_licensed_encoder_and_gif_export_works_offline(self):
        self.page.evaluate("typebit.setPlaybackRate(2)")
        with self.page.expect_download() as pending:
            self.page.click("#typebit-download-html")
        saved = self.base / "saved.html"
        pending.value.save_as(saved)
        markup = saved.read_text(encoding="utf-8")
        self.assertIn("Copyright (c) 2017 Matt DesLauriers", markup)
        self.assertEqual(external_resources(markup), [])
        self.page.goto(saved.as_uri())
        state = self.page.evaluate("typebit.getState()")
        self.assertEqual(state["status"], "idle")
        self.assertEqual(state["playbackRate"], 2)
        gif = self.download_gif("saved-page.gif")
        self.assert_gif(gif, 1800)
        self.assertEqual(self.page.evaluate("typebit.getState()"), state)

    def test_encoder_error_restores_state_and_reenables_controls(self):
        self.page.evaluate("""() => {
            typebit.seek(.6); typebit.setPlaybackRate(2);
            window.gifenc = {...window.gifenc, quantize() { throw new Error('Injected encoder failure'); }};
        }""")
        before = self.page.evaluate("typebit.getState()")
        self.page.click("#typebit-download-gif")
        self.page.wait_for_function("document.getElementById('typebit-export-status').textContent === 'Injected encoder failure'")
        self.wait_finished()
        self.assertEqual(self.page.evaluate("typebit.getState()"), before)
        self.assertEqual(self.downloads, [])
        for identity in ("typebit-control", "typebit-speed", "typebit-progress", "typebit-download-gif"):
            self.assertTrue(self.page.locator(f"#{identity}").is_enabled())
        self.assertFalse(self.page.locator("#typebit-cancel-export").is_visible())
        self.assert_project_unchanged()

    def test_excessive_gif_rejected_without_mutating_state_or_downloading(self):
        configure_project(self.project, duration=300, playback_rate=.25)
        self.html = Path(render_project(self.project)["html"])
        self.page.goto(self.html.as_uri())
        self.page.evaluate("typebit.seek(100)")
        before = self.page.evaluate("typebit.getState()")
        self.page.click("#typebit-download-gif")
        self.page.wait_for_function("document.getElementById('typebit-export-status').textContent.includes('600 frames')")
        self.wait_finished()
        self.assertEqual(self.page.evaluate("typebit.getState()"), before)
        self.assertEqual(self.downloads, [])

    def test_lowering_fps_resolves_frame_limit_before_a_real_download(self):
        configure_project(self.project, duration=60, playback_rate=1)
        self.html = Path(render_project(self.project)["html"])
        self.page.goto(self.html.as_uri())
        self.page.locator("#typebit-gif-options").evaluate("element => element.open = true")
        estimate = self.page.locator("#typebit-gif-estimate")
        self.assertEqual(estimate.get_attribute("data-error"), "true")
        self.assertIn("600 frames", estimate.inner_text())
        self.page.select_option("#typebit-gif-fps", "5")
        self.assertEqual(estimate.get_attribute("data-error"), "false")
        self.assertIn("60.8 seconds", estimate.inner_text())
        saved = self.download_gif("lower-fps.gif")
        with Image.open(saved) as image:
            self.assertEqual(image.n_frames, 301)
            duration = 0
            for index in range(image.n_frames):
                image.seek(index)
                duration += image.info["duration"]
            self.assertEqual(duration, 60800)
        self.assertEqual(self.page.evaluate("typebit.getState().status"), "idle")


class VendoredGifIntegrityTests(unittest.TestCase):
    def test_release_checksums_and_inline_license_are_preserved(self):
        vendor = ROOT / "skills/tracegif/assets/vendor"
        provenance = json.loads((vendor / "gifenc.provenance.json").read_text(encoding="utf-8"))
        bundle = (vendor / "gifenc.js").read_bytes()
        license = (vendor / "gifenc.LICENSE.md").read_bytes()
        self.assertEqual(provenance["version"], "1.0.3")
        self.assertEqual(hashlib.sha256(bundle).hexdigest(), provenance["vendored_sha256"])
        self.assertEqual(hashlib.sha256(license).hexdigest(), provenance["license_sha256"])
        self.assertIn(b"Copyright (c) 2017 Matt DesLauriers", bundle)
        self.assertNotIn(b"sourceMappingURL", bundle)


if __name__ == "__main__":
    unittest.main()
