"""Case rebuilds must not silently reuse stale authored contours or raster sources."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import build_cases as cases


class CaseInputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="typebit-case-inputs-")
        self.root = Path(self.temporary.name)
        self.examples = self.root / "examples"
        self.examples.mkdir()
        self.case = {"slug": "demo", "kind": "logo", "source": "source.png",
                     "contours": "contours.svg", "source_svg": "authored.svg"}
        self.svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path id="box" d="M4 4H12V12H4Z" fill="#fff"/></svg>'
        for name in ("contours.svg", "authored.svg"):
            (self.examples / name).write_text(self.svg, encoding="utf-8")
        Image.new("RGBA", (16, 16), (255, 255, 255, 0)).save(self.examples / "source.png")
        self.raster_record = {"schema_version": 1, "method": "unit-test fixture",
                              "source_svg": {"file": "authored.svg", "sha256": cases.sha256(self.examples / "authored.svg")},
                              "output_png": {"file": "source.png", "sha256": cases.sha256(self.examples / "source.png")}}
        (self.examples / "source.png.source.json").write_text(json.dumps(self.raster_record), encoding="utf-8")
        self.build = self.root / "build"
        self.project = self.build / "demo"
        cases.prepare_project(self.examples / "source.png", self.project, kind="logo",
                              contours=self.examples / "contours.svg")
        cases.record_case_inputs(self.project, cases.case_input_hashes(self.case, self.examples), self.raster_record)
        (self.examples / "cases.json").write_text(json.dumps({"cases": [self.case]}), encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def test_unchanged_inputs_and_prepared_geometry_can_be_reused(self):
        cases.validate_case_reuse(self.project, self.case, cases.case_input_hashes(self.case, self.examples))
        self.assertEqual(cases.raster_provenance(self.examples / "source.png", self.examples / "authored.svg"), self.raster_record)

    def assert_build_rejects_before_mutation(self):
        before = {path.name: path.read_bytes() for path in self.project.iterdir() if path.is_file()}
        with patch.object(cases, "ROOT", self.root), patch.object(cases, "sync_playwright") as browser, \
                patch.object(cases, "configure_project") as configure:
            with self.assertRaisesRegex(ValueError, "new --build-root"):
                cases.build_cases(self.build, self.root / "media", refresh_raster=True)
            browser.assert_not_called()
            configure.assert_not_called()
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.project.iterdir() if path.is_file()})

    def test_changed_authored_contours_reject_unchanged_png_before_refresh(self):
        (self.examples / "contours.svg").write_text(self.svg.replace("H12", "H11"), encoding="utf-8")
        self.assert_build_rejects_before_mutation()

    def test_changed_authoring_svg_rejects_unchanged_png_before_refresh(self):
        (self.examples / "authored.svg").write_text(self.svg.replace("H12", "H10"), encoding="utf-8")
        self.assert_build_rejects_before_mutation()

    def test_edited_prepared_contours_cannot_silently_replace_authored_input(self):
        path = self.project / "contours.svg"
        path.write_text(path.read_text(encoding="utf-8").replace("H12", "H9"), encoding="utf-8")
        self.assert_build_rejects_before_mutation()

    def test_legacy_project_without_input_record_requires_new_build_root(self):
        (self.project / "case-inputs.json").unlink()
        self.assert_build_rejects_before_mutation()

    def test_fresh_project_rejects_stale_png_pair_without_rasterizing(self):
        (self.examples / "authored.svg").write_text(self.svg.replace("H12", "H8"), encoding="utf-8")
        with patch.object(cases, "ROOT", self.root), patch.object(cases, "sync_playwright") as browser, \
                patch.object(cases, "prepare_project") as prepare:
            with self.assertRaisesRegex(ValueError, "--refresh-raster"):
                cases.build_cases(self.root / "fresh", self.root / "media")
            browser.assert_not_called()
            prepare.assert_not_called()

    def test_changed_png_also_invalidates_render_provenance(self):
        Image.new("RGBA", (16, 16), (255, 255, 255, 255)).save(self.examples / "source.png")
        with self.assertRaisesRegex(ValueError, "--refresh-raster"):
            cases.raster_provenance(self.examples / "source.png", self.examples / "authored.svg")


class CaseDimensionTests(unittest.TestCase):
    def test_landscape_square_and_portrait_frames_keep_source_aspect(self):
        for box, expected in [([0, 0, 800, 520], (480, 312)),
                              ([0, 0, 600, 600], (480, 480)),
                              ([0, 0, 600, 760], (480, 608)),
                              ([10, 20, 840, 520], (480, 297))]:
            with self.subTest(box=box):
                dimensions = cases.frame_dimensions(box)
                self.assertEqual((dimensions["width"], dimensions["height"]), expected)

    def test_invalid_or_extreme_aspect_ratios_fail_explicitly(self):
        for box in ([0, 0, 0, 760], [0, 0, 600, -1], [0, 0, float("nan"), 1], [0, 0, 1, 9000]):
            with self.subTest(box=box), self.assertRaises(ValueError):
                cases.frame_dimensions(box)

    def test_raster_checks_accept_small_fixtures_without_badge_coordinates(self):
        with tempfile.TemporaryDirectory(prefix="tracegif-small-case-") as temporary:
            project = Path(temporary)
            (project / "assets").mkdir()
            image = Image.new("RGBA", (8, 12), (0, 0, 0, 0))
            image.putpixel((4, 6), (255, 255, 255, 255))
            image.save(project / "assets/source.png")
            image.save(project / "assets/subject.png")
            manifest = {"source": {"path": "assets/source.png"}}
            result = cases.raster_preservation_checks(project, manifest, {})
            self.assertTrue(result["original_rgba_preserved"])
            self.assertEqual(result["pixel_probes"], [])
            result = cases.raster_preservation_checks(project, manifest, {
                "pixel_probes": [{"name": "white", "xy": [4, 6], "rgba": [255, 255, 255, 255]}]})
            self.assertTrue(result["pixel_probes"][0]["passed"])


class CasePreviewBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = cases.sync_playwright().start()
        try:
            cls.browser = cls.runtime.chromium.launch(headless=True)
        except Exception as exc:
            cls.runtime.stop()
            if os.environ.get("CI"):
                raise RuntimeError("CI must provide Chromium for case aspect-ratio checks.") from exc
            raise unittest.SkipTest(f"Chromium is unavailable: {exc}") from exc

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.runtime.stop()

    def test_actual_source_and_final_panels_match_for_three_aspect_ratios(self):
        with tempfile.TemporaryDirectory(prefix="tracegif-case-aspect-") as temporary:
            root = Path(temporary)
            for width, height in [(300, 180), (240, 240), (180, 270)]:
                with self.subTest(size=(width, height)):
                    source = root / f"source-{width}-{height}.svg"
                    source.write_text(
                        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
                        f'<path id="shape" fill="#9a4533" d="M10 10H{width-10}V{height-10}H10Z"/></svg>', encoding="utf-8")
                    raster = source.with_suffix(".png")
                    cases.make_raster_source(self.browser, source, raster)
                    with Image.open(raster) as image:
                        self.assertEqual(image.size, (width, height))
                        self.assertEqual(image.convert("RGBA").getpixel((0, 0))[3], 0)
                    project = root / f"project-{width}-{height}"
                    media = root / f"media-{width}-{height}"
                    media.mkdir()
                    cases.prepare_project(source, project, kind="svg", duration=6)
                    cases.render_project(project)
                    cases.capture_preview(self.browser, source, project, media, {"duration": 6, "matte": "#FAF5EA"})
                    panel_height = round(480 * height / width)
                    with Image.open(media / "preview.png") as preview:
                        self.assertEqual(preview.size, (1488, panel_height + 66))
                        first = preview.crop((12, 54, 492, 54 + panel_height))
                        final = preview.crop((996, 54, 1476, 54 + panel_height))
                        self.assertIsNone(ImageChops.difference(first, final).getbbox())


if __name__ == "__main__":
    unittest.main()
