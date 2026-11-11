"""Portable-project provenance and archive boundary regressions."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/tracegif/scripts"))
from typebitlib.core import TypeBitError, _project_zip, package_project, prepare_project, render_project
from typebitlib.export import export_project

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80"><path id="outline" d="M20 20H80V60H20Z" fill="#2563eb"/></svg>'


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="typebit-archive-test-")
        self.base = Path(self.temp.name)
        self.source = self.base / "source.svg"
        self.source.write_text(SVG, encoding="utf-8")
        self.project = self.base / "project"
        prepare_project(self.source, self.project)
        render_project(self.project)

    def tearDown(self):
        self.temp.cleanup()

    def set_review(self, review):
        path = self.project / "project.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["visual_review"] = review
        path.write_text(json.dumps(manifest), encoding="utf-8")

    def html_hash(self):
        return hashlib.sha256((self.project / "animation.html").read_bytes()).hexdigest()

    def report(self):
        folder = self.project / "verification"
        folder.mkdir(exist_ok=True)
        (folder / "report.json").write_text(json.dumps({"html_sha256": self.html_hash(), "automated_status": "unverified",
                                                        "visual_review": {"status": "unverified"}}), encoding="utf-8")
        (folder / "report.md").write_text("# Verification\n\nVisual review: **unverified**.\n\nMore evidence.\n", encoding="utf-8")

    def extracted_project(self):
        result = package_project(self.project)
        restored = self.base / "restored"
        with zipfile.ZipFile(result["zip"]) as archive:
            archive.extractall(restored)
        self.assertFalse((restored / ".last-render.zip").exists())
        return restored

    def test_extracted_project_can_be_repackaged_without_private_snapshot(self):
        restored = self.extracted_project()
        result = package_project(restored)
        self.assertEqual(result["status"], "packaged")
        with zipfile.ZipFile(result["zip"]) as archive:
            self.assertEqual(archive.read("scene.svg"), (self.project / "scene.svg").read_bytes())

    def test_extracted_project_rejects_changed_scene_before_rerender(self):
        restored = self.extracted_project()
        scene = restored / "scene.svg"
        scene.write_text(scene.read_text(encoding="utf-8").replace("#2563eb", "#ff0000"), encoding="utf-8")
        with self.assertRaisesRegex(TypeBitError, "assets changed|settings changed"):
            package_project(restored)

    def test_archive_excludes_private_cache_revision_and_self(self):
        for relative in [".private-note", "revisions/old.txt", "__pycache__/cache.pyc"]:
            path = self.project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic ignored data", encoding="utf-8")
        destination = self.project / "bundle.zip"
        _project_zip(self.project, destination)
        with zipfile.ZipFile(destination) as archive:
            names = set(archive.namelist())
            self.assertIn("scene.svg", names)
            self.assertNotIn("bundle.zip", names)
            self.assertFalse(any(name.startswith((".", "revisions/", "__pycache__/")) for name in names))

    def test_package_checks_export_hashes_current_html_and_required_sidecars(self):
        result = export_project(self.project, format="html")
        output, evidence = Path(result["output"]), Path(result["report"])
        original_output, original_evidence = output.read_bytes(), evidence.read_bytes()
        package_project(self.project)
        for problem in ("changed_file", "stale_html", "missing_report"):
            with self.subTest(problem=problem):
                output.write_bytes(original_output)
                evidence.write_bytes(original_evidence)
                if problem == "changed_file":
                    output.write_bytes(b"corrupt export")
                elif problem == "stale_html":
                    report = json.loads(original_evidence)
                    report["source_html_sha256"] = "0" * 64
                    evidence.write_text(json.dumps(report), encoding="utf-8")
                else:
                    evidence.unlink()
                with self.assertRaisesRegex(TypeBitError, "export evidence|Export evidence"):
                    package_project(self.project)

    def test_package_protects_private_snapshot_and_unrelated_archive(self):
        snapshot = self.project / ".last-render.zip"
        before = snapshot.read_bytes()
        with self.assertRaisesRegex(TypeBitError, "private snapshots"):
            package_project(self.project, snapshot)
        self.assertEqual(snapshot.read_bytes(), before)
        unrelated = self.base / "unrelated.zip"
        unrelated.write_bytes(b"keep this existing file")
        with self.assertRaisesRegex(TypeBitError, "unrelated archive"):
            package_project(self.project, unrelated)
        self.assertEqual(unrelated.read_bytes(), b"keep this existing file")

    def test_replacing_package_is_atomic_and_does_not_include_prior_self(self):
        output = self.project / "exports/project.zip"
        package_project(self.project, output)
        before = output.read_bytes()

        def failed_archive(project, temporary, **options):
            temporary.write_bytes(b"unfinished")
            raise OSError("Synthetic interrupted archive")

        with patch("typebitlib.core._project_zip", side_effect=failed_archive), self.assertRaises(OSError):
            package_project(self.project, output)
        self.assertEqual(output.read_bytes(), before)
        self.assertEqual(list(output.parent.glob(".typebit-package-*")), [])
        package_project(self.project, output)
        with zipfile.ZipFile(output) as archive:
            self.assertNotIn("exports/project.zip", archive.namelist())
            self.assertIn("animation.html", archive.namelist())

    @unittest.skipUnless(os.name == "nt", "NTFS junction behavior applies to Windows")
    def test_archive_does_not_follow_junction_outside_project(self):
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "sentinel.txt").write_text("Synthetic outside-project data", encoding="utf-8")
        junction = self.project / "linked-assets"
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        command = f"New-Item -ItemType Junction -Path {quote(junction)} -Target {quote(outside)} | Out-Null"
        try:
            result = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.TimeoutExpired) as exc:
            self.skipTest(f"Junction setup unavailable: {exc}")
        if result.returncode:
            self.skipTest("Junction creation is unavailable in this environment")
        self.assertTrue(junction.is_junction())
        destination = self.base / "safe.zip"
        _project_zip(self.project, destination)
        with zipfile.ZipFile(destination) as archive:
            self.assertFalse(any("sentinel" in name for name in archive.namelist()))

    def test_visual_review_requires_current_hash_without_browser_report(self):
        self.set_review({"status": "reviewed", "html_sha256": "stale", "notes": ["Synthetic test review"]})
        with self.assertRaisesRegex(TypeBitError, "Visual review"):
            package_project(self.project)

    def test_visual_review_requires_notes_with_browser_report(self):
        self.report()
        self.set_review({"status": "reviewed", "html_sha256": self.html_hash(), "notes": []})
        with self.assertRaisesRegex(TypeBitError, "Visual review"):
            package_project(self.project)

    def test_valid_visual_review_is_copied_into_packaged_evidence(self):
        self.report()
        review = {"status": "reviewed", "html_sha256": self.html_hash(), "notes": ["Synthetic test review"]}
        self.set_review(review)
        result = package_project(self.project)
        self.assertEqual(result["visual_review"], "reviewed")
        with zipfile.ZipFile(result["zip"]) as archive:
            report = json.loads(archive.read("verification/report.json"))
            self.assertEqual(report["visual_review"], review)
            self.assertIn("Synthetic test review", archive.read("verification/report.md").decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
