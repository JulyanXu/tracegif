"""Behavioral checks for source preservation, portable export and revision safety."""

import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/typebit-line-animation/scripts"))
from typebitlib.core import (TypeBitError, border_white_candidate, package_project,
                             prepare_project, render_project, sanitize_svg)

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 80"><path id="body" fill="#2563eb" d="M20 20H100V60H20Z"/><path id="white" fill="white" d="M50 30H70V50H50Z"/></svg>'


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.source = self.base / "source.svg"
        self.source.write_text(SVG, encoding="utf-8")
        self.project = self.base / "project"

    def tearDown(self):
        self.tmp.cleanup()

    def prepare(self):
        return prepare_project(self.source, self.project)

    def manifest(self):
        return json.loads((self.project / "project.json").read_text())

    def update(self, data):
        (self.project / "project.json").write_text(json.dumps(data), encoding="utf-8")

    def test_prepare_preserves_input_and_refuses_overwrite(self):
        self.prepare()
        self.assertEqual(self.source.read_bytes(), (self.project / "assets/source.svg").read_bytes())
        with self.assertRaises(TypeBitError):
            self.prepare()

    def test_native_export_is_self_contained(self):
        self.prepare()
        result = render_project(self.project)
        from typebitlib.verify import external_resources
        markup = Path(result["html"]).read_text(encoding="utf-8")
        self.assertEqual(external_resources(markup), [])
        self.assertIn('id="art-white"', markup)
        self.assertIn('id="trace-body"', markup)
        self.assertNotIn('src="http', markup)

    def test_revisions_keep_previous_scene_and_timing(self):
        self.prepare()
        render_project(self.project)
        first = self.manifest()
        modified = self.manifest()
        modified["layers"][0]["label"] = "Main silhouette"
        self.update(modified)
        render_project(self.project)
        with zipfile.ZipFile(self.project / "revisions/r0001.zip") as archive:
            previous = json.loads(archive.read("project.json"))
        self.assertEqual(first, previous)
        self.assertEqual(self.manifest()["revision"], 2)

    def test_package_rejects_unrendered_edits(self):
        self.prepare()
        render_project(self.project)
        modified = self.manifest()
        modified["brand_color"] = "#ff0000"
        self.update(modified)
        with self.assertRaisesRegex(TypeBitError, "settings changed"):
            package_project(self.project)

    def test_package_is_portable(self):
        self.prepare()
        render_project(self.project)
        result = package_project(self.project)
        with zipfile.ZipFile(result["zip"]) as archive:
            names = archive.namelist()
            self.assertIn("scene.svg", names)
            self.assertIn("project.json", names)
            self.assertIn("animation.html", names)
            self.assertIn("assets/source.svg", names)
            self.assertFalse(any(name.startswith(".") for name in names))

    def test_original_source_change_is_detected(self):
        self.prepare()
        (self.project / "assets/source.svg").write_text("changed")
        with self.assertRaisesRegex(TypeBitError, "Original source changed"):
            render_project(self.project)

    def test_asset_path_cannot_escape_project(self):
        self.prepare()
        data = self.manifest()
        data["scene"] = "../source.svg"
        self.update(data)
        with self.assertRaisesRegex(TypeBitError, "escapes"):
            render_project(self.project)

    def test_stale_verification_cannot_be_packaged(self):
        self.prepare()
        render_project(self.project)
        folder = self.project / "verification"
        folder.mkdir()
        (folder / "report.json").write_text(json.dumps({"html_sha256": "wrong", "automated_status": "passed"}))
        with self.assertRaisesRegex(TypeBitError, "different HTML"):
            package_project(self.project)

    def test_raster_without_host_contours_or_mask_is_not_a_finished_animation(self):
        source = self.base / "photo.png"
        Image.new("RGB", (120, 80), "gray").save(source)
        result = prepare_project(source, self.project, kind="photo")
        self.assertEqual(result["status"], "needs_input")
        self.assertEqual(len(result["needs"]), 2)
        with self.assertRaises(TypeBitError):
            render_project(self.project)

    def test_border_white_removal_preserves_enclosed_white(self):
        image = Image.new("RGBA", (60, 60), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((10, 10, 50, 50), fill="#2563eb")
        draw.rectangle((20, 20, 40, 40), fill="white")
        clean = border_white_candidate(image)
        self.assertEqual(clean.getpixel((0, 0))[3], 0)
        self.assertEqual(clean.getpixel((30, 30)), (255, 255, 255, 255))
        self.assertEqual(image.getpixel((0, 0))[3], 255)

    def test_photo_mask_keeps_original_rgb_pixels(self):
        source = self.base / "photo.png"
        original = Image.new("RGB", (120, 80))
        for y in range(80):
            for x in range(120):
                original.putpixel((x, y), (x * 2, y * 3, (x+y) % 256))
        original.save(source)
        mask = self.base / "mask.png"
        matte = Image.new("L", (120, 80))
        ImageDraw.Draw(matte).ellipse((20, 10, 100, 70), fill=255)
        matte.save(mask)
        result = prepare_project(source, self.project, kind="photo", mask=mask, contours=self.source)
        self.assertEqual(result["status"], "prepared")
        with Image.open(self.project / "assets/subject.png") as subject:
            self.assertEqual(subject.getpixel((60, 40))[:3], original.getpixel((60, 40)))
            self.assertEqual(subject.getpixel((0, 0))[3], 0)
        self.assertTrue(self.manifest()["processing"]["approximation"])
        render_project(self.project)

    def test_wrong_mask_or_contour_size_is_rejected(self):
        source = self.base / "source.png"
        Image.new("RGBA", (120, 80), (0, 0, 255, 0)).save(source)
        mask = self.base / "mask.png"
        Image.new("L", (10, 10), 255).save(mask)
        with self.assertRaisesRegex(TypeBitError, "dimensions"):
            prepare_project(source, self.project, mask=mask, contours=self.source)
        self.source.write_text(SVG.replace("120 80", "100 100"))
        with self.assertRaisesRegex(TypeBitError, "alignment"):
            prepare_project(source, self.project, contours=self.source)

    def test_text_without_font_fails_with_actionable_message(self):
        text = SVG.replace("</svg>", '<text x="5" y="5">ABC</text></svg>')
        with self.assertRaisesRegex(TypeBitError, "font"):
            sanitize_svg(text)

    def test_svg_scripts_removed_and_external_resources_rejected(self):
        root, _, warnings = sanitize_svg(SVG.replace("</svg>", '<script>alert(1)</script></svg>').replace('id="body"', 'id="body" onclick="alert(1)"'))
        self.assertEqual(len(warnings), 2)
        self.assertNotIn("script", "".join(node.tag for node in root.iter()))
        for fragment in ['<image href="https://example.com/image.png"/>', '<style>path{fill:url(https://example.com/x)}</style>', '<foreignObject><div>unsafe</div></foreignObject><image href="file:///private"/>']:
            with self.assertRaises(TypeBitError):
                sanitize_svg(SVG.replace("</svg>", fragment + "</svg>"))

    def test_svg_resource_checks_handle_html_case_normalization_and_css_escapes(self):
        for fragment in ['<image HREF="https://example.invalid/image.png"/>',
                         '<rect fill="u\\72l(https://example.invalid/x.svg#p)"/>',
                         '<rect STYLE="fill:u\\72l(https://example.invalid/x.svg#p)"/>']:
            with self.assertRaises(TypeBitError):
                sanitize_svg(SVG.replace("</svg>", fragment + "</svg>"))

    def test_entity_expansion_is_rejected(self):
        with self.assertRaises(TypeBitError):
            sanitize_svg('<!DOCTYPE svg [<!ENTITY x "hello">]><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><title>&x;</title></svg>')

    def test_mixed_visible_use_cannot_flash_before_playback(self):
        source = SVG.replace('</svg>', '<defs><path id="symbol" d="M0 0H5V5Z"/></defs><use href="#symbol"/></svg>')
        with self.assertRaisesRegex(TypeBitError, "Expand visible"):
            sanitize_svg(source)

    def test_extracted_project_detects_edits_without_private_snapshot(self):
        self.prepare()
        render_project(self.project)
        (self.project / ".last-render.zip").unlink()
        data = self.manifest()
        data["brand_color"] = "#ff0000"
        self.update(data)
        with self.assertRaisesRegex(TypeBitError, "settings changed"):
            package_project(self.project)

    def test_css_is_scoped_and_colors_are_not_rewritten_as_ids(self):
        source = SVG.replace('<path id="body"', '<style>body{background:#fff} #fff:hover{fill:#fff} .x{stroke:#fff}</style><path id="fff" class="x"')
        self.source.write_text(source)
        self.prepare()
        render_project(self.project)
        markup = (self.project / "animation.html").read_text(encoding="utf-8")
        self.assertIn('#typebit-art body{background:#fff}', markup)
        self.assertIn('#typebit-traces #trace-fff:hover{fill:#fff}', markup)
        self.assertNotIn('fill:#art-fff', markup)

    def test_nonzero_viewbox_and_root_id_are_preserved(self):
        self.source.write_text(SVG.replace('viewBox="0 0 120 80"', 'id="original" viewBox="-20 -10 120 80"'))
        self.prepare()
        render_project(self.project)
        markup = (self.project / "animation.html").read_text(encoding="utf-8")
        self.assertIn('id="art-original"', markup)
        self.assertIn('x="-20" y="-10" width="120" height="80"', markup)

    def test_invalid_timing_and_missing_layers_are_rejected(self):
        self.prepare()
        data = self.manifest()
        data["layers"][0]["duration"] = float("nan")
        self.update(data)
        with self.assertRaisesRegex(TypeBitError, "finite"):
            render_project(self.project)
        data["layers"][0]["duration"] = 1
        data["layers"].pop()
        self.update(data)
        with self.assertRaisesRegex(TypeBitError, "Every drawable"):
            render_project(self.project)


if __name__ == "__main__":
    unittest.main()
