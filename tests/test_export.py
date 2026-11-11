"""Real export outputs, timing, alpha, provenance, and source protection."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageSequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/tracegif/scripts"))
from typebitlib.core import TypeBitError, prepare_project, render_project
from typebitlib.export import export_project


SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 80">'
       '<path id="body" fill="#b83220" stroke="#683a20" d="M20 15H100V65H20Z"/>'
       '<path id="white" fill="white" d="M50 30H70V50H50Z"/></svg>')


class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                browser.close()
        except Exception as exc:
            if os.environ.get("CI"):
                raise RuntimeError("CI must install Playwright and Chromium for export tests.") from exc
            raise unittest.SkipTest(f"Chromium is unavailable: {str(exc).splitlines()[0]}") from exc

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="typebit-export-")
        self.base = Path(self.temporary.name)
        self.source = self.base / "source.svg"
        self.source.write_text(SVG, encoding="utf-8")
        self.project = self.base / "project"
        prepare_project(self.source, self.project, duration=1)
        render_project(self.project)

    def tearDown(self):
        self.temporary.cleanup()

    def test_png_preserves_source_pixels_and_transparency_and_time_selects_frame(self):
        result = export_project(self.project, format="png")
        with Image.open(result["output"]) as image:
            self.assertEqual(image.size, (120, 80))
            self.assertEqual(image.mode, "RGBA")
            self.assertEqual(image.getpixel((0, 0))[3], 0)
            self.assertEqual(image.getpixel((30, 30)), (184, 50, 32, 255))
            self.assertEqual(image.getpixel((60, 40)), (255, 255, 255, 255))
        report = json.loads(Path(result["report"]).read_text(encoding="utf-8"))
        self.assertEqual(report["output_sha256"], hashlib.sha256(Path(result["output"]).read_bytes()).hexdigest())
        self.assertEqual(report["source_html_sha256"], hashlib.sha256((self.project / "animation.html").read_bytes()).hexdigest())
        self.assertTrue(report["validation"]["offline"])
        start = export_project(self.project, format="png", time=0, output=self.base / "start.png")
        with Image.open(start["output"]) as image:
            self.assertIsNone(image.getchannel("A").getbbox(), "Waiting frame should contain no artwork or toolbar")

    def test_gif_uses_actual_frames_selected_speed_matte_and_final_hold(self):
        result = export_project(self.project, format="gif", width=120, fps=8, speed=2, background="#16324F")
        self.assertEqual(result["duration_ms"], 1300)
        self.assertEqual(result["effective_duration"], .5)
        self.assertEqual(result["transparency"], "opaque_matte")
        with Image.open(result["output"]) as image:
            frames = [frame.convert("RGB") for frame in ImageSequence.Iterator(image)]
            image.seek(0)
            durations = [frame.info["duration"] for frame in ImageSequence.Iterator(image)]
            self.assertGreater(len(frames), 1)
            self.assertEqual(sum(durations), 1300)
            self.assertEqual(frames[0].getpixel((60, 40)), (22, 50, 79))
            self.assertEqual(frames[-1].getpixel((60, 40)), (255, 255, 255))
            self.assertEqual(frames[-1].getpixel((30, 30)), (184, 50, 32))
            self.assertEqual(frames[-1].getpixel((0, 0)), (22, 50, 79))
            self.assertEqual(image.info["loop"], 0)

    def test_html_export_is_portable_and_speed_override_does_not_edit_project(self):
        from playwright.sync_api import sync_playwright

        source_bytes = (self.project / "animation.html").read_bytes()
        unchanged = export_project(self.project, format="html")
        self.assertEqual(Path(unchanged["output"]).read_bytes(), source_bytes)
        faster = export_project(self.project, format="html", output=self.base / "faster.html", speed=2)
        self.assertEqual((self.project / "animation.html").read_bytes(), source_bytes)
        markup = Path(faster["output"]).read_text(encoding="utf-8")
        config = json.loads(re.search(r'id="typebit-config">(.*?)</script>', markup, re.S)[1])
        self.assertEqual(config["playback_rate"], 2)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(offline=True)
            page = context.new_page()
            page.goto(Path(faster["output"]).as_uri())
            state = page.evaluate("typebit.getState()")
            self.assertEqual(state["status"], "idle")
            self.assertEqual(state["time"], 0)
            # This also proves the copied file uses the standalone rate configuration.
            self.assertEqual(state["playbackRate"], 2)
            browser.close()
        # A previous genuine export is replaceable using its matching sidecar.
        again = export_project(self.project, format="html")
        self.assertEqual(unchanged["output_sha256"], again["output_sha256"])

    def test_export_rejects_stale_project_and_protects_existing_files(self):
        original = (self.project / "animation.html").read_bytes()
        with self.assertRaisesRegex(TypeBitError, "source files|animation.html"):
            export_project(self.project, format="html", output=self.project / "animation.html")
        unrelated = self.base / "original.png"
        unrelated.write_bytes(b"irreplaceable source")
        with self.assertRaisesRegex(TypeBitError, "unrelated"):
            export_project(self.project, format="png", output=unrelated)
        self.assertEqual(unrelated.read_bytes(), b"irreplaceable source")
        self.assertEqual((self.project / "animation.html").read_bytes(), original)
        scene = self.project / "scene.svg"
        scene.write_text(scene.read_text(encoding="utf-8").replace("#b83220", "#cc2233"), encoding="utf-8")
        with self.assertRaises(TypeBitError):
            export_project(self.project, format="png")

    def test_invalid_or_excessive_exports_fail_before_browser_capture(self):
        cases = [
            {"format": "png", "width": 0}, {"format": "png", "width": 33.5},
            {"format": "png", "time": 2}, {"format": "png", "time": float("nan")},
            {"format": "png", "fps": 12},
            {"format": "png", "speed": 2}, {"format": "gif", "background": "transparent"},
            {"format": "gif", "background": "url(https://example.invalid/image.png)"},
            {"format": "gif", "fps": 31}, {"format": "gif", "width": 2048, "fps": 30, "speed": .25},
            {"format": "gif", "speed": 0}, {"format": "gif", "time": .5},
            {"format": "html", "width": 120}, {"format": "html", "background": "#FFFFFF"},
            {"format": "mp4"},
        ]
        for options in cases:
            with self.subTest(options=options), self.assertRaises(TypeBitError):
                export_project(self.project, **options)
        self.assertFalse((self.project / "exports").exists())


if __name__ == "__main__":
    unittest.main()
