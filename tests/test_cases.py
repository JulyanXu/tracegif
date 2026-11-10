"""Case rebuilds must not silently reuse stale authored contours or raster sources."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

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


if __name__ == "__main__":
    unittest.main()
