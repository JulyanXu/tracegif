"""Release case layout and verification bindings must survive repackaging."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills/tracegif/scripts"))
from tools.build_release import build_case_bundle, build_release
from typebitlib import __version__


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def encoded(value):
    return json.dumps(value).encode("utf-8")


class CaseReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="typebit-release-test-")
        self.root = Path(self.temporary.name)
        self.output = self.root / "release.zip"
        self.html = b"<!doctype html><title>Release fixture</title>"
        self.identity = digest(self.html)
        self.report = {"html_sha256": self.identity, "automated_status": "passed"}
        self.payloads = {"gif": b"GIF89a fixture", "png": b"PNG fixture"}

    def tearDown(self):
        self.temporary.cleanup()

    def fixture(self, changes=None, entry_changes=None):
        members = {"animation.html": self.html, "verification/report.json": encoded(self.report)}
        for extension, payload in self.payloads.items():
            members[f"exports/animation.{extension}"] = payload
            members[f"exports/animation.{extension}.export.json"] = encoded({
                "source_html_sha256": self.identity, "output_sha256": digest(payload)})
        members.update(changes or {})
        package = self.root / "demo-project.zip"
        with zipfile.ZipFile(package, "w") as archive:
            for name, payload in members.items():
                archive.writestr(name, payload)
        entry = {"slug": "demo", "title": "Demo", "html_sha256": self.identity,
                 "project_zip": package.name, "project_zip_sha256": digest(package.read_bytes()),
                 "automated_status": "passed", "assets": {
                     "final.png": {"file": "final.png", "sha256": digest(self.payloads["png"])},
                     "preview.png": {"file": "preview.png", "sha256": "not-shipped"}}}
        entry.update(entry_changes or {})
        manifest = {"schema_version": 1, "typebit_version": "0.3.0", "license": "MIT", "cases": [entry]}
        (self.root / "manifest.json").write_bytes(encoded(manifest))
        return members

    def sample_project(self):
        project = self.root / "example"
        for name, payload in self.fixture().items():
            destination = project / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
        (self.root / "example-project.zip").write_bytes((self.root / "demo-project.zip").read_bytes())
        return project

    def test_every_release_manifest_path_and_hash_matches_an_included_file(self):
        self.fixture()
        original_manifest = (self.root / "manifest.json").read_bytes()
        build_case_bundle(self.root, self.output)
        self.assertEqual((self.root / "manifest.json").read_bytes(), original_manifest)
        with zipfile.ZipFile(self.output) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(manifest["artifact_type"], "public-case-release")
            entry = manifest["cases"][0]
            self.assertEqual(digest(archive.read(entry["project_zip"])), entry["project_zip_sha256"])
            self.assertNotIn("final.png", entry["assets"])
            self.assertNotIn("preview.png", entry["assets"])
            self.assertIn("animation.png", entry["assets"])
            included = {entry["project_zip"]}
            for asset in entry["assets"].values():
                self.assertEqual(digest(archive.read(asset["file"])), asset["sha256"])
                included.add(asset["file"])
            self.assertEqual(included, set(archive.namelist()) - {"manifest.json", "README.txt"})
            report = json.loads(archive.read(entry["assets"]["report.json"]["file"]))
            self.assertEqual(report["html_sha256"], self.identity)
            for extension in self.payloads:
                sidecar = entry["assets"][f"animation.{extension}.export.json"]["file"]
                self.assertEqual(json.loads(archive.read(sidecar))["source_html_sha256"], self.identity)

    def test_rejects_changed_project_package(self):
        self.fixture(entry_changes={"project_zip_sha256": "stale"})
        with self.assertRaisesRegex(ValueError, "package is stale"):
            build_case_bundle(self.root, self.output)

    def test_rejects_mismatched_evidence_even_with_a_current_package_checksum(self):
        cases = [
            ({"verification/report.json": encoded({**self.report, "html_sha256": "stale"})}, "mismatched HTML"),
            ({"verification/report.json": encoded({**self.report, "automated_status": "failed"})}, "mismatched HTML"),
            ({"exports/animation.gif": b"changed GIF"}, "stale GIF"),
            ({"exports/animation.png.export.json": encoded({
                "source_html_sha256": "stale", "output_sha256": digest(self.payloads["png"])})}, "stale PNG"),
        ]
        for changes, message in cases:
            with self.subTest(member=next(iter(changes)), message=message):
                self.fixture(changes)
                with self.assertRaisesRegex(ValueError, message):
                    build_case_bundle(self.root, self.output)

    def test_sample_reexport_requires_repackaging_before_release_files_are_created(self):
        project = self.sample_project()
        exported = project / "exports/animation.gif"
        exported.write_bytes(b"GIF89a new size and frame rate")
        sidecar = project / "exports/animation.gif.export.json"
        sidecar.write_bytes(encoded({"source_html_sha256": self.identity,
                                    "output_sha256": digest(exported.read_bytes())}))
        output = self.root / "dist"
        with self.assertRaisesRegex(ValueError, "package is stale: exports/animation.gif"):
            build_release(project, output, __version__, self.root)
        self.assertFalse(output.exists())
        with zipfile.ZipFile(self.root / "example-project.zip", "w") as archive:
            for source in project.rglob("*"):
                if source.is_file():
                    archive.write(source, source.relative_to(project).as_posix())
        self.assertEqual(build_release(project, output, __version__, self.root)["status"], "built")
        with zipfile.ZipFile(output / "tracegif-example-project.zip") as archive:
            self.assertEqual(archive.read("exports/animation.gif"), (output / "tracegif-example.gif").read_bytes())

    def test_sample_report_and_sidecar_changes_require_repackaging(self):
        for relative, extra in [("verification/report.json", {"visual_review": {"status": "reviewed"}}),
                                ("exports/animation.png.export.json", {"width": 640})]:
            with self.subTest(member=relative):
                project = self.sample_project()
                path = project / relative
                path.write_bytes(encoded({**json.loads(path.read_bytes()), **extra}))
                with self.assertRaisesRegex(ValueError, "package is stale: " + relative):
                    build_release(project, self.root / "dist", __version__, self.root)
                self.assertFalse((self.root / "dist").exists())

    def test_sample_rejects_html_available_only_in_a_nested_revision(self):
        project = self.sample_project()
        with zipfile.ZipFile(self.root / "example-project.zip", "w") as archive:
            for source in project.rglob("*"):
                if source.is_file():
                    relative = source.relative_to(project).as_posix()
                    archive.write(source, "revisions/animation.html" if relative == "animation.html" else relative)
        with self.assertRaisesRegex(ValueError, "missing animation.html"):
            build_release(project, self.root / "dist", __version__, self.root)
        self.assertFalse((self.root / "dist").exists())


if __name__ == "__main__":
    unittest.main()
