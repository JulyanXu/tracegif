from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "typebit-line-animation" / "scripts"))
from typebitlib.verify import external_resources, verify_html


class ResourceAuditTests(unittest.TestCase):
    def test_embedded_images_fonts_and_local_svg_fragments_are_allowed(self):
        html = '''<svg><use href="#outline"/><image href="data:image/png;base64,AA=="/></svg>
        <style>@font-face{src:url('data:font/woff2;base64,AA==')} .a{clip-path:url(#clip)}</style>'''
        self.assertEqual(external_resources(html), [])

    def test_local_files_and_cdn_links_are_not_self_contained(self):
        html = '<script src="player.js"></script><img src="https://example.invalid/p.png"><link href="style.css">'
        self.assertEqual(external_resources(html), ["https://example.invalid/p.png", "player.js", "style.css"])

    def test_css_import_and_inline_background_are_detected(self):
        html = '''<style>@import "https://example.invalid/style.css";</style>
        <div style="background:url('./picture.png')"></div>'''
        self.assertEqual(external_resources(html), ["./picture.png", "https://example.invalid/style.css"])

    def test_js_code_is_not_mistaken_for_stylesheet_resources(self):
        self.assertEqual(external_resources('<script>const s="url(not-a-resource)";</script>'), [])

    def test_missing_html_fails_with_a_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = verify_html(root / "missing.html", root / "evidence")
            self.assertEqual(result["automated_status"], "failed")
            self.assertEqual(result["visual_review"]["status"], "unverified")
            saved = json.loads((root / "evidence" / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["checks"][0]["name"], "html_exists")

    def test_invalid_encoding_fails_without_browser(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = Path(tmp) / "broken.html"
            html.write_bytes(b"\xff\xfe")
            result = verify_html(html)
            self.assertEqual(result["automated_status"], "failed")
            self.assertEqual(result["html_sha256"], hashlib.sha256(b"\xff\xfe").hexdigest())

    def test_missing_browser_is_unverified_not_passed(self):
        manager = MagicMock()
        manager.__enter__.return_value.chromium.launch.side_effect = RuntimeError("Chromium is not installed")
        api = SimpleNamespace(sync_playwright=lambda: manager)
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {"playwright.sync_api": api}):
            html = Path(tmp) / "animation.html"
            html.write_text("<!doctype html><p>Test</p>", encoding="utf-8")
            result = verify_html(html)
            self.assertEqual(result["automated_status"], "unverified")
            self.assertEqual(result["visual_review"]["status"], "unverified")
            self.assertEqual(result["checks"][-1]["status"], "unverified")

    def test_external_dependency_still_fails_when_browser_is_missing(self):
        manager = MagicMock()
        manager.__enter__.return_value.chromium.launch.side_effect = RuntimeError("Chromium is not installed")
        api = SimpleNamespace(sync_playwright=lambda: manager)
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {"playwright.sync_api": api}):
            html = Path(tmp) / "animation.html"
            html.write_text('<script src="https://example.invalid/player.js"></script>', encoding="utf-8")
            result = verify_html(html)
            self.assertEqual(result["automated_status"], "failed")


if __name__ == "__main__":
    unittest.main()
