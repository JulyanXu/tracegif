"""Offline browser checks for rate changes, seeking, and real downloads."""
from __future__ import annotations

import base64
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/typebit-line-animation/scripts"))
from typebitlib.core import prepare_project, render_project
from typebitlib.verify import external_resources


class PlayerControlsTests(unittest.TestCase):
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
        self.temporary = tempfile.TemporaryDirectory(prefix="typebit-player-")
        self.base = Path(self.temporary.name)
        self.context = self.browser.new_context(offline=True, accept_downloads=True,
                                                viewport={"width": 320, "height": 240})
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        pixels = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
        for y in range(4, 20):
            for x in range(4, 20):
                pixels.putpixel((x, y), (255, 255, 255, 255) if x < 12 else (210, 80, 35, 180))
        buffer = io.BytesIO()
        pixels.save(buffer, format="PNG")
        raster = base64.b64encode(buffer.getvalue()).decode("ascii")
        source = self.base / "source.svg"
        source.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="240" viewBox="40 60 320 240">'
            '<style>.subject { stroke:#72512c; stroke-width:3; }</style>'
            '<defs><linearGradient id="paint"><stop stop-color="#df7738"/>'
            '<stop offset="1" stop-color="#f6c151"/></linearGradient>'
            '<clipPath id="clip"><circle cx="200" cy="180" r="78"/></clipPath></defs>'
            '<rect id="subject" class="subject" x="115" y="95" width="170" height="170" '
            'fill="url(#paint)" clip-path="url(#clip)"/>'
            '<path id="accent" d="M125 105L275 105" stroke="url(#paint)" stroke-width="4" fill="none"/>'
            f'<image id="pixels" x="176" y="156" width="48" height="48" href="data:image/png;base64,{raster}"/>'
            '</svg>', encoding="utf-8")
        self.project = self.base / "project"
        prepare_project(source, self.project, kind="svg")
        path = self.project / "project.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["playback_rate"] = 1.5
        path.write_text(json.dumps(manifest), encoding="utf-8")
        self.html = Path(render_project(self.project)["html"])
        self.page.goto(self.html.as_uri())
        self.page.wait_for_function("Boolean(window.typebit)")

    def tearDown(self):
        self.assertEqual(self.errors, [])
        self.context.close()
        self.temporary.cleanup()

    def test_speed_changes_preserve_position_and_apply_to_elapsed_time(self):
        state = self.page.evaluate("typebit.getState()")
        self.assertEqual(state["status"], "idle")
        self.assertEqual(state["time"], 0)
        self.assertEqual(state["playbackRate"], 1.5)
        self.assertAlmostEqual(state["effectiveDuration"], 10 / 1.5)
        self.page.click("#typebit-control")
        self.page.wait_for_timeout(100)
        change = self.page.evaluate("""() => {
            const before = typebit.getState();
            const after = typebit.setPlaybackRate(4);
            return {before, after};
        }""")
        self.assertLess(abs(change["after"]["time"] - change["before"]["time"]), .03)
        self.assertEqual(change["after"]["status"], "playing")
        advancement = self.page.evaluate("""async () => {
            const start = performance.now(), before = typebit.getState().time;
            await new Promise(resolve => setTimeout(resolve, 160));
            return {wall: (performance.now()-start)/1000, timeline: typebit.getState().time-before};
        }""")
        self.assertAlmostEqual(advancement["timeline"], advancement["wall"] * 4, delta=.05)
        paused = self.page.evaluate("typebit.pause(); typebit.getState()")
        self.page.select_option("#typebit-speed", "0.5")
        self.page.wait_for_timeout(80)
        after = self.page.evaluate("typebit.getState()")
        self.assertEqual(after["status"], "paused")
        self.assertAlmostEqual(after["time"], paused["time"], places=5)
        self.assertEqual(after["playbackRate"], .5)
        self.assertEqual(after["effectiveDuration"], 20)
        self.page.evaluate("typebit.setPlaybackRate(1.25)")
        self.assertEqual(self.page.locator("#typebit-speed").input_value(), "1.25")
        for invalid in (0, .1, 5, "NaN"):
            self.assertTrue(self.page.evaluate("""value => {
                try { typebit.setPlaybackRate(value); return false; }
                catch (error) { return error instanceof RangeError; }
            }""", invalid))

    def test_scrubber_uses_native_keys_without_starting_global_playback(self):
        self.page.evaluate("""() => {
            const range = document.getElementById('typebit-progress');
            range.value = '4.5'; range.dispatchEvent(new Event('input', {bubbles:true}));
        }""")
        self.assertEqual(self.page.evaluate("typebit.getState().status"), "paused")
        self.assertAlmostEqual(self.page.evaluate("typebit.getState().time"), 4.5)
        self.page.locator("#typebit-progress").focus()
        self.page.keyboard.press("ArrowRight")
        self.assertEqual(self.page.evaluate("typebit.getState().status"), "paused")
        self.assertGreater(self.page.evaluate("typebit.getState().time"), 4.5)
        self.page.click("#typebit-replay")
        self.assertEqual(self.page.evaluate("typebit.getState().status"), "playing")
        self.assertLess(self.page.evaluate("typebit.getState().time"), .5)

    def test_saved_html_keeps_selected_speed_and_reopens_idle_offline(self):
        self.page.evaluate("typebit.seek(6); typebit.setPlaybackRate(2)")
        with self.page.expect_download() as expected:
            self.page.click("#typebit-download-html")
        download = expected.value
        self.assertTrue(download.suggested_filename.endswith(".html"))
        saved = self.base / "saved.html"
        download.save_as(saved)
        self.assertEqual(external_resources(saved.read_text(encoding="utf-8")), [])
        requests = []
        self.page.on("request", lambda request: requests.append(request.url))
        self.page.goto(saved.as_uri())
        self.page.wait_for_timeout(120)
        state = self.page.evaluate("typebit.getState()")
        self.assertEqual(state["status"], "idle")
        self.assertEqual(state["time"], 0)
        self.assertEqual(state["playbackRate"], 2)
        self.assertEqual(state["effectiveDuration"], 5)
        self.assertEqual(self.page.locator("#typebit-speed").input_value(), "2")
        self.assertFalse(any(url.startswith(("https:", "http:")) for url in requests))
        self.assertTrue(self.page.locator("#typebit-controls").is_visible())
        self.page.click("#typebit-control")
        self.assertEqual(self.page.evaluate("typebit.getState().status"), "playing")

    def test_current_frame_png_has_original_dimensions_alpha_and_rendered_pixels(self):
        for seconds in (5, 10):
            with self.subTest(seconds=seconds):
                self.page.evaluate("t => typebit.seek(t)", seconds)
                self.page.evaluate("typebit.setControlsVisible(false)")
                expected = Image.open(io.BytesIO(self.page.screenshot(omit_background=True))).convert("RGBA")
                self.page.evaluate("typebit.setControlsVisible(true)")
                with self.page.expect_download() as pending:
                    self.page.click("#typebit-download-png")
                saved = self.base / f"frame-{seconds}.png"
                pending.value.save_as(saved)
                actual = Image.open(saved).convert("RGBA")
                self.assertEqual(actual.size, (320, 240))
                self.assertEqual(actual.getpixel((0, 0))[3], 0)
                delta = ImageChops.difference(expected, actual)
                self.assertLessEqual(max(high for _, high in delta.getextrema()), 3)
                self.assertEqual(self.page.evaluate("typebit.getState().time"), seconds)

    def test_controls_fit_a_small_screen_and_hide_as_one_unit(self):
        for width in (320, 450, 600, 790, 960):
            with self.subTest(width=width):
                self.page.set_viewport_size({"width": width, "height": 700})
                bounds = self.page.locator("#typebit-controls").bounding_box()
                self.assertGreaterEqual(bounds["x"], 0)
                self.assertLessEqual(bounds["x"] + bounds["width"], width)
                for identity in ("typebit-control", "typebit-replay", "typebit-speed", "typebit-progress",
                                 "typebit-time", "typebit-download-html", "typebit-download-png"):
                    box = self.page.locator(f"#{identity}").bounding_box()
                    self.assertGreaterEqual(box["x"], bounds["x"])
                    self.assertLessEqual(box["x"] + box["width"], bounds["x"] + bounds["width"])
                self.assertTrue(self.page.locator("#typebit-controls label").evaluate("e => e.scrollWidth <= e.clientWidth + 1"))
        self.page.evaluate("typebit.setControlsVisible(false)")
        self.assertFalse(self.page.locator("#typebit-controls").is_visible())
        self.page.evaluate("typebit.setControlsVisible(true)")
        self.assertTrue(self.page.locator("#typebit-controls").is_visible())


if __name__ == "__main__":
    unittest.main()
