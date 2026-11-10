"""A real photographic fixture exercises the host-supplied mask/contour path."""

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image, ImageChops, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/typebit-line-animation/scripts"))
from typebitlib.core import TypeBitError, package_project, prepare_project, render_project
from typebitlib.verify import external_resources

FIXTURES = ROOT / "examples/source"
PHOTO = FIXTURES / "blue-marble.jpg"
MASK = FIXTURES / "blue-marble-mask.png"
CONTOURS = FIXTURES / "blue-marble-contours.svg"


class RealPhotoTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name) / "blue-marble"

    def tearDown(self):
        self.temporary.cleanup()

    def prepare(self):
        return prepare_project(PHOTO, self.project, kind="photo", mask=MASK, contours=CONTOURS)

    def test_real_photo_keeps_original_rgb_and_uses_only_supplied_alpha(self):
        self.assertEqual(self.prepare()["status"], "prepared")
        self.assertEqual(PHOTO.read_bytes(), (self.project / "assets/source.jpg").read_bytes())
        with Image.open(PHOTO) as image:
            original = ImageOps.exif_transpose(image).convert("RGB")
        with Image.open(MASK) as image:
            mask = image.convert("L")
        with Image.open(self.project / "assets/subject.png") as image:
            subject = image.convert("RGBA")
        # Compare every decoded color pixel, including bright interior clouds.
        self.assertIsNone(ImageChops.difference(original, subject.convert("RGB")).getbbox())
        self.assertIsNone(ImageChops.difference(mask, subject.getchannel("A")).getbbox())
        self.assertEqual(subject.getpixel((520, 520))[3], 255)
        for point in [(0, 0), (1040, 0), (0, 1040), (1040, 1040), (10, 520)]:
            self.assertEqual(subject.getpixel(point)[3], 0)

    def test_real_photo_renders_portable_project_with_approximation_disclosed(self):
        self.prepare()
        render = render_project(self.project)
        html = Path(render["html"]).read_text(encoding="utf-8")
        self.assertEqual(external_resources(html), [])
        manifest = json.loads((self.project / "project.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["source"]["kind"], "photo")
        self.assertTrue(manifest["processing"]["approximation"])
        self.assertEqual(manifest["processing"]["needs"], [])
        self.assertEqual({layer["phase"] for layer in manifest["layers"]}, {"main", "secondary", "details"})
        package = package_project(self.project)
        with zipfile.ZipFile(package["zip"]) as archive:
            self.assertEqual(archive.read("assets/source.jpg"), PHOTO.read_bytes())
            self.assertEqual(archive.read("assets/mask.png"), MASK.read_bytes())
            self.assertIn("contours.svg", archive.namelist())
            self.assertIn("animation.html", archive.namelist())

    def test_real_opaque_photo_without_mask_does_not_claim_subject_isolation(self):
        result = prepare_project(PHOTO, self.project, kind="photo", contours=CONTOURS)
        self.assertEqual(result["status"], "needs_input")
        self.assertTrue(any("mask" in message for message in result["needs"]))
        with self.assertRaisesRegex(TypeBitError, "needs"):
            render_project(self.project)


if __name__ == "__main__":
    unittest.main()
