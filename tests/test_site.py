"""Exercise the public homepage against the real exported player, not a poster."""
from __future__ import annotations

import functools
import hashlib
import json
import os
import tempfile
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class PublicCaseIntegrityTests(unittest.TestCase):
    def test_published_player_and_reports_match_the_gallery_manifest(self):
        manifest = json.loads((ROOT / "docs/cases/manifest.json").read_text(encoding="utf-8"))
        slugs = set()
        for case in manifest["cases"]:
            with self.subTest(case=case["slug"]):
                self.assertNotIn(case["slug"], slugs)
                slugs.add(case["slug"])
                folder = ROOT / "docs/cases" / case["slug"]
                self.assertEqual(folder.resolve().parent, (ROOT / "docs/cases").resolve())
                for asset in case["assets"].values():
                    path = folder / asset["file"]
                    self.assertEqual(path.resolve().parent, folder.resolve())
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), asset["sha256"])
                html_hash = hashlib.sha256((folder / "animation.html").read_bytes()).hexdigest()
                self.assertEqual(case["html_sha256"], html_hash)
                report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
                self.assertEqual(report["html_sha256"], html_hash)
                self.assertEqual(report["automated_status"], "passed")
                self.assertEqual(case["automated_status"], "passed")
                provenance = case.get("input_provenance", {}).get("authored_inputs", {})
                for source in provenance.values():
                    path = ROOT / "examples" / source["file"]
                    self.assertTrue(path.resolve().is_relative_to((ROOT / "examples").resolve()))
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), source["sha256"])


class LiveSiteTests(unittest.TestCase):
    # The standalone verifier overrides these; unittest discovers the same local checks.
    base_url = None
    evidence_dir = None

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
        cls.server = None
        if cls.base_url is None:
            handler = functools.partial(QuietHandler, directory=str(ROOT / "docs"))
            cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
            cls.thread.start()
            cls.url = f"http://127.0.0.1:{cls.server.server_port}/"
        else:
            cls.url = cls.base_url.rstrip("/") + "/"
        if cls.evidence_dir:
            cls.evidence_dir = Path(cls.evidence_dir)
            cls.evidence_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.runtime.stop()
        if cls.server:
            cls.server.shutdown()
            cls.server.server_close()
            cls.thread.join(timeout=5)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tracegif-site-")
        self.context = self.browser.new_context(accept_downloads=True,
                                                viewport={"width": 1440, "height": 900})
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))

    def tearDown(self):
        self.context.close()
        self.temp.cleanup()
        self.assertEqual(self.errors, [])

    def open_site(self):
        response = self.page.goto(self.url)
        self.assertEqual(response.status, 200)
        self.page.wait_for_function("document.querySelector('#demo-frame')?.contentWindow?.tracegif")
        self.page.locator("#start-demo").wait_for(state="visible")
        return self.frame()

    def frame(self):
        return self.page.locator("#demo-frame").element_handle().content_frame()

    def state(self):
        return self.frame().evaluate("tracegif.getState()")

    def screenshot(self, name):
        if self.evidence_dir:
            # Give the homepage's state label one poll to observe native player actions.
            self.page.wait_for_timeout(230)
            scroll_y = self.page.evaluate("window.scrollY")
            self.page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
            self.page.screenshot(path=str(self.evidence_dir / name), full_page=True)
            self.page.evaluate("top => window.scrollTo({top, behavior: 'instant'})", scroll_y)

    def select_scene(self, slug):
        self.page.locator(f'[data-case="{slug}"]').click()
        self.page.wait_for_function("slug => { const f = document.querySelector('#demo-frame'); return f?.contentWindow?.location.pathname.includes('/' + slug + '/') && Boolean(f.contentWindow?.tracegif); }", arg=slug)
        self.page.wait_for_function("document.querySelector('#demo-frame').contentWindow.tracegif.getState().status === 'idle'")
        return self.frame()

    def test_homepage_runs_real_player_and_native_transport(self):
        frame = self.open_site()
        self.assertEqual(self.state()["status"], "idle")
        self.assertEqual(self.state()["time"], 0)
        self.assertGreater(frame.locator("svg path").count(), 10)
        self.assertTrue(frame.locator("#typebit-controls").is_visible())
        self.assertEqual(self.page.locator(".hero img").count(), 0)
        for selector in ("#typebit-control", "#typebit-speed"):
            box = frame.locator(selector).bounding_box()
            self.assertGreaterEqual(box["y"], 0)
            self.assertLessEqual(box["y"] + box["height"], 900)
        if self.evidence_dir:
            self.page.screenshot(path=str(self.evidence_dir / "desktop-first-viewport.png"))
        self.screenshot("desktop-idle.png")
        self.page.locator("#start-demo").click()
        frame.wait_for_function("tracegif.getState().time > .15")
        self.assertEqual(self.state()["status"], "playing")
        frame.locator("#typebit-control").click()
        paused = self.state()
        self.assertEqual(paused["status"], "paused")
        frame.locator("#typebit-speed").select_option("2")
        self.assertEqual(self.state()["playbackRate"], 2)
        self.assertAlmostEqual(self.state()["time"], paused["time"], places=4)
        frame.locator("#typebit-progress").evaluate("element => {element.value = element.max * .58; element.dispatchEvent(new Event('input', {bubbles:true}));}")
        self.assertEqual(self.state()["status"], "paused")
        self.assertAlmostEqual(self.state()["time"], self.state()["duration"] * .58, places=2)
        self.screenshot("desktop-drawing.png")
        frame.evaluate("tracegif.seek(tracegif.getState().duration)")
        self.screenshot("desktop-final.png")
        frame.locator("#typebit-replay").click()
        self.assertEqual(self.state()["status"], "playing")
        self.assertLess(self.state()["time"], 1)

    def test_case_switches_change_the_real_document_and_mobile_controls_fit(self):
        self.open_site()
        self.page.locator('[data-filter="all"]').click()
        slugs = self.page.locator("[data-case]").evaluate_all("items => items.map(item => item.dataset.case)")
        self.assertGreaterEqual(len(slugs), 7)
        first_url = self.frame().url
        alternative = next(slug for slug in slugs if f"/{slug}/" not in first_url)
        frame = self.select_scene(alternative)
        self.assertNotEqual(frame.url, first_url)
        self.assertEqual(self.page.locator(f'[data-case="{alternative}"]').get_attribute("aria-pressed"), "true")
        self.assertIn(f"/{alternative}/animation.html", self.page.locator("#open-player").get_attribute("href"))
        self.page.set_viewport_size({"width": 375, "height": 812})
        frame = self.select_scene("celebration-card")
        frame.evaluate("tracegif.seek(tracegif.getState().duration)")
        self.page.locator("#demo-frame").scroll_into_view_if_needed()
        self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))
        self.assertTrue(frame.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))
        controls = frame.locator("#typebit-controls").bounding_box()
        iframe = self.page.locator("#demo-frame").bounding_box()
        self.assertGreaterEqual(controls["x"], iframe["x"] - 1)
        self.assertLessEqual(controls["x"] + controls["width"], iframe["x"] + iframe["width"] + 1)
        frame.locator("#typebit-gif-options summary").click()
        self.assertTrue(frame.locator("#typebit-gif-options").evaluate("element => element.open"))
        self.screenshot("mobile-player.png")
        self.page.locator("#language-toggle").click()
        self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))
        self.assertEqual(self.state()["time"], self.state()["duration"])

    def test_embedded_player_downloads_real_png_and_gif(self):
        self.open_site()
        self.page.locator('[data-filter="all"]').click()
        frame = self.select_scene("leaf-studio")
        frame.evaluate("tracegif.seek(tracegif.getState().duration); tracegif.setPlaybackRate(4)")
        before = self.state()
        target = self.evidence_dir or Path(self.temp.name)
        with self.page.expect_download(timeout=15000) as pending:
            frame.locator("#typebit-download-png").click()
        png = target / "embedded-player.png"
        pending.value.save_as(png)
        with Image.open(png) as image:
            self.assertEqual(image.size, (640, 480))
            self.assertEqual(image.mode, "RGBA")
            self.assertEqual(image.getpixel((0, 0))[3], 0)
            self.assertIsNotNone(image.getbbox())
        frame.locator("#typebit-gif-options summary").click()
        frame.locator("#typebit-gif-width").select_option("240")
        frame.locator("#typebit-gif-fps").select_option("5")
        with self.page.expect_download(timeout=30000) as pending:
            frame.locator("#typebit-download-gif").click()
        gif = target / "embedded-player.gif"
        pending.value.save_as(gif)
        frame.wait_for_function("!tracegif.getState().exporting")
        self.assertEqual(self.state(), before)
        with Image.open(gif) as image:
            self.assertEqual(image.size, (240, 180))
            self.assertGreater(image.n_frames, 2)
            opening = image.convert("RGB")
            duration = 0
            for i in range(image.n_frames):
                image.seek(i)
                duration += image.info["duration"]
            self.assertAlmostEqual(duration, before["effectiveDuration"] * 1000 + 800, delta=10)
            self.assertIsNotNone(ImageChops.difference(opening, image.convert("RGB")).getbbox())

    def test_embed_controls_do_not_cover_art_and_saved_html_remains_standalone(self):
        frame = self.open_site()
        frame.wait_for_function("document.querySelector('#tracegif-embed-layout')")
        self.assertLessEqual(frame.locator('#typebit-stage').bounding_box()['y'] +
                             frame.locator('#typebit-stage').bounding_box()['height'],
                             frame.locator('#typebit-controls').bounding_box()['y'] + 1)
        self.page.set_viewport_size({'width': 375, 'height': 812})
        self.page.locator('#demo-frame').scroll_into_view_if_needed()
        frame.locator('#typebit-gif-options summary').click()
        frame.wait_for_function("() => { const a = document.querySelector('#typebit-stage').getBoundingClientRect(); const b = document.querySelector('#typebit-controls').getBoundingClientRect(); return a.height > 0 && a.bottom <= b.top + 1; }")
        frame.locator('#typebit-speed').select_option('2')
        with self.page.expect_download(timeout=15000) as pending:
            frame.locator('#typebit-download-html').click()
        saved = Path(self.temp.name) / 'standalone.html'
        pending.value.save_as(saved)
        self.assertNotIn('tracegif-embed-layout', saved.read_text(encoding='utf-8'))
        offline = self.browser.new_context(offline=True)
        try:
            reopened = offline.new_page()
            reopened.goto(saved.as_uri())
            reopened.wait_for_function('window.tracegif')
            state = reopened.evaluate('tracegif.getState()')
            self.assertEqual(state['status'], 'idle')
            self.assertEqual(state['playbackRate'], 2)
            reopened.locator('#typebit-control').click()
            reopened.wait_for_function('tracegif.getState().time > .05')
        finally:
            offline.close()

    def test_scene_and_language_deep_link_open_the_requested_live_player(self):
        manifest = json.loads((ROOT / "docs/cases/manifest.json").read_text(encoding="utf-8"))
        case = next((item for item in manifest["cases"] if item["slug"] == "night-market"),
                    manifest["cases"][0])
        self.page.goto(self.url + f'?lang=zh&scene={case["slug"]}')
        self.page.wait_for_function("document.querySelector('#demo-frame')?.contentWindow?.tracegif")
        self.assertEqual(self.page.locator("html").get_attribute("lang"), "zh-CN")
        self.assertEqual(self.page.locator("#demo-title").inner_text(), case["title_zh"])
        self.assertIn(f'/{case["slug"]}/animation.html', self.frame().url)
        self.assertEqual(self.state()["status"], "idle")
        self.frame().evaluate("tracegif.seek(tracegif.getState().duration)")
        self.screenshot("desktop-chinese.png")
        self.page.locator("#language-toggle").click()
        self.assertEqual(self.page.locator("html").get_attribute("lang"), "en")
        self.assertEqual(self.page.locator("#demo-title").inner_text(), case["title"])
        self.assertEqual(self.state()["time"], self.state()["duration"])
        self.assertIn("lang=en", self.page.url)

    def test_missing_manifest_has_retryable_failure(self):
        self.page.route("**/cases/manifest.json*", lambda route: route.fulfill(status=503, body="Temporarily unavailable"))
        self.page.goto(self.url)
        self.page.locator("#load-error").wait_for(state="visible")
        self.assertTrue(self.page.locator("#retry-load").is_visible())
        self.page.unroute("**/cases/manifest.json*")
        self.page.locator("#retry-load").click()
        self.page.wait_for_function("document.querySelector('#demo-frame')?.contentWindow?.tracegif")
        self.assertFalse(self.page.locator("#load-error").is_visible())
        self.assertEqual(self.state()["status"], "idle")

    def test_unavailable_scene_does_not_leave_a_fake_playable_preview(self):
        self.open_site()
        self.page.locator('[data-filter="all"]').click()
        self.page.route("**/cases/leaf-studio/animation.html", lambda route: route.fulfill(status=503, body="Temporarily unavailable"))
        self.page.locator('[data-case="leaf-studio"]').click()
        self.page.locator("#load-error").wait_for(state="visible")
        self.assertFalse(self.page.locator("#start-demo").is_visible())
        self.page.unroute("**/cases/leaf-studio/animation.html")
        self.page.locator("#retry-load").click()
        self.page.wait_for_function("document.querySelector('#demo-frame')?.contentWindow?.tracegif")
        self.assertFalse(self.page.locator("#load-error").is_visible())
        self.assertEqual(self.state()["status"], "idle")


if __name__ == "__main__":
    unittest.main()
