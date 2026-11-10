"""Real-browser regression tests for imported SVG fidelity.

These checks use source SVG pixels as the reference, rather than comparing two
TypeBit exports. Local runs can skip if Chromium is unavailable; CI installs it.
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/typebit-line-animation/scripts"))
from typebitlib.core import prepare_project, render_project


def svg(content, *, view_box="0 0 320 240", identity="source-root"):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" id="{identity}" '
            f'width="320" height="240" viewBox="{view_box}">{content}</svg>')


class SvgBrowserPreservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            if os.environ.get("CI"):
                raise RuntimeError("CI must install the locked Playwright dependency.") from exc
            raise unittest.SkipTest("Playwright is unavailable; install locked skill dependencies.") from exc
        cls.runtime = sync_playwright().start()
        try:
            cls.browser = cls.runtime.chromium.launch(headless=True)
        except Exception as exc:
            cls.runtime.stop()
            if os.environ.get("CI"):
                raise RuntimeError("CI must provide a runnable Chromium browser.") from exc
            raise unittest.SkipTest(f"Chromium is unavailable: {str(exc).splitlines()[0]}") from exc

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.runtime.stop()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="typebit-svg-browser-")
        self.base = Path(self.temporary.name)
        self.context = self.browser.new_context(
            viewport={"width": 320, "height": 240}, device_scale_factor=1, offline=True
        )
        self.source_page = self.context.new_page()
        self.export_page = self.context.new_page()
        self.errors = []
        self.export_page.on("pageerror", lambda error: self.errors.append(str(error)))

    def tearDown(self):
        self.context.close()
        self.temporary.cleanup()

    def render_pair(self, markup):
        source = self.base / "source.svg"
        source.write_text(markup, encoding="utf-8")
        project = self.base / "project"
        prepare_project(source, project, kind="svg")
        manifest_path = project / "project.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["doodle"] = False
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        result = render_project(project)
        self.source_page.goto(source.as_uri())
        self.export_page.goto(Path(result["html"]).as_uri())
        self.export_page.evaluate("typebit.setControlsVisible(false); typebit.seek(10)")
        self.assertEqual(self.errors, [])

    def assert_final_pixels_match_source(self):
        expected = Image.open(io.BytesIO(self.source_page.screenshot(omit_background=True))).convert("RGBA")
        actual = Image.open(io.BytesIO(self.export_page.screenshot(omit_background=True))).convert("RGBA")
        self.assertEqual(actual.size, expected.size)
        difference = ImageChops.difference(expected, actual)
        maximum_channel_error = max(high for _, high in difference.getextrema())
        # At most two 8-bit levels permit insignificant rasterization rounding.
        self.assertLessEqual(maximum_channel_error, 2, "Final SVG pixels differ from the original source")

    def assert_matching_box(self, source_id, export_id):
        expected = self.source_page.locator(f"[id='{source_id}']").bounding_box()
        actual = self.export_page.locator(f"[id='{export_id}']").bounding_box()
        self.assertIsNotNone(expected)
        self.assertIsNotNone(actual)
        for field in ("x", "y", "width", "height"):
            self.assertAlmostEqual(actual[field], expected[field], places=5, msg=field)

    def test_nonzero_viewbox_origin_preserves_position_and_pixels(self):
        self.render_pair(svg(
            '<rect id="body" x="70" y="100" width="140" height="80" rx="12" fill="#2563eb"/>'
            '<circle id="window" cx="140" cy="135" r="16" fill="white"/>',
            view_box="40 60 320 240",
        ))
        self.assert_matching_box("body", "art-body")
        self.assert_matching_box("window", "art-window")
        self.assert_final_pixels_match_source()

    def test_root_id_and_child_combinator_styles_survive_and_remain_scoped(self):
        self.render_pair(svg(
            '<style>body { background: #ff0000; } '
            'path { stroke: #12316a; stroke-width: 4; } '
            '#logo > g > .subject { fill: #f59e0b; } '
            '#logo .window { fill: #ffffff; }</style>'
            '<g><path id="body" class="subject" d="M40 40H250V190H40Z"/>'
            '<path id="window" class="window" d="M100 80H160V140H100Z"/></g>',
            identity="logo",
        ))
        self.assertEqual(self.export_page.locator("#art-logo").count(), 1)
        self.assertEqual(self.export_page.locator("#trace-logo").count(), 1)
        self.assertEqual(
            self.export_page.locator("#art-body").evaluate("element => getComputedStyle(element).fill"),
            "rgb(245, 158, 11)",
        )
        self.assertEqual(
            self.export_page.locator("body").evaluate("element => getComputedStyle(element).backgroundColor"),
            "rgba(0, 0, 0, 0)",
        )
        # Source-wide path rules must not style geometry outside the imported SVG.
        outside_stroke = self.export_page.evaluate("""() => {
            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.id = 'outside-probe';
            path.setAttribute('d', 'M1 1L2 2');
            document.getElementById('typebit-scene').appendChild(path);
            const stroke = getComputedStyle(path).stroke;
            path.remove();
            return stroke;
        }""")
        self.assertEqual(outside_stroke, "none")
        self.assert_matching_box("body", "art-body")
        self.assert_final_pixels_match_source()

    def test_gradient_clip_and_mask_references_preserve_real_pixels(self):
        self.render_pair(svg(
            '<defs>'
            '<linearGradient id="paint"><stop stop-color="#2563eb"/>'
            '<stop offset="1" stop-color="#f59e0b"/></linearGradient>'
            '<clipPath id="clip"><circle cx="160" cy="120" r="85"/></clipPath>'
            '<mask id="cutout" maskUnits="userSpaceOnUse" x="0" y="0" width="320" height="240">'
            '<rect width="320" height="240" fill="white"/>'
            '<circle cx="160" cy="120" r="25" fill="black"/></mask>'
            '</defs>'
            '<rect id="body" x="40" y="20" width="240" height="200" '
            'fill="url(#paint)" clip-path="url(#clip)" mask="url(#cutout)"/>'
        ))
        for identity in ("paint", "clip", "cutout"):
            self.assertEqual(self.export_page.locator(f"#art-{identity}").count(), 1)
            self.assertEqual(self.export_page.locator(f"#trace-{identity}").count(), 1)
        attributes = self.export_page.locator("#art-body").evaluate("""element => ({
            fill: element.getAttribute('fill'), clip: element.getAttribute('clip-path'),
            mask: element.getAttribute('mask')
        })""")
        self.assertEqual(attributes, {"fill": "url(#art-paint)", "clip": "url(#art-clip)", "mask": "url(#art-cutout)"})
        self.assertEqual(
            self.export_page.locator("#trace-cutout rect").evaluate("element => element.style.strokeDasharray"), ""
        )
        self.assert_final_pixels_match_source()

    def test_hex_color_identical_to_shape_id_is_not_rewritten_as_selector(self):
        self.render_pair(svg(
            '<style>#fff { fill: #fff; stroke: #12316a; stroke-width: 3; } '
            '.back { fill: #2563eb; }</style>'
            '<rect id="back" class="back" x="40" y="30" width="240" height="180"/>'
            '<path id="fff" d="M110 70H210V170H110Z"/>'
        ))
        self.assertEqual(
            self.export_page.locator("#art-fff").evaluate("element => getComputedStyle(element).fill"),
            "rgb(255, 255, 255)",
        )
        self.assert_final_pixels_match_source()

    def doodle_export(self, name, setting="prepared"):
        """Leave the lower third empty so any added decoration is observable."""
        source = self.base / f"{name}.svg"
        source.write_text(svg(
            '<rect id="subject" x="120" y="20" width="80" height="60" fill="#333333"/>'
        ), encoding="utf-8")
        project = self.base / name
        prepare_project(source, project, kind="svg")
        manifest_path = project / "project.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if setting == "omitted":
            manifest.pop("doodle", None)
        elif setting != "prepared":
            manifest["doodle"] = setting
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        result = render_project(project)
        return Path(result["html"])

    def assert_no_added_doodle_pixels(self, html):
        self.export_page.goto(html.as_uri())
        self.export_page.evaluate("typebit.setControlsVisible(false)")
        for time in (1, 5, 10):
            with self.subTest(time=time):
                self.export_page.evaluate("time => typebit.seek(time)", time)
                frame = Image.open(io.BytesIO(self.export_page.screenshot(omit_background=True))).convert("RGBA")
                # Source geometry ends at y=80. The lower third must stay truly clear.
                self.assertIsNone(frame.getchannel("A").crop((0, 150, 320, 240)).getbbox())
                self.assertEqual(self.export_page.locator("#typebit-doodle path").count(), 0)
        self.assertEqual(self.errors, [])

    def test_new_and_unspecified_projects_do_not_add_blue_strokes(self):
        for setting in ("prepared", "omitted", False):
            with self.subTest(setting=setting):
                self.assert_no_added_doodle_pixels(self.doodle_export(f"case-{setting}", setting))

    def test_requested_doodles_remain_visible_behind_artwork(self):
        html = self.doodle_export("requested", True)
        self.export_page.goto(html.as_uri())
        self.export_page.evaluate("typebit.setControlsVisible(false)")
        self.assertGreater(self.export_page.locator("#typebit-doodle path").count(), 0)
        self.assertTrue(self.export_page.evaluate("""() => {
            const doodle = document.getElementById('typebit-doodle');
            const art = document.getElementById('typebit-art');
            return doodle.parentElement === art.parentElement &&
                Boolean(doodle.compareDocumentPosition(art) & Node.DOCUMENT_POSITION_FOLLOWING);
        }"""))
        for time in (1, 5, 10):
            with self.subTest(time=time):
                self.export_page.evaluate("time => typebit.seek(time)", time)
                frame = Image.open(io.BytesIO(self.export_page.screenshot(omit_background=True))).convert("RGBA")
                self.assertIsNotNone(frame.getchannel("A").crop((0, 150, 320, 240)).getbbox())
        self.assertEqual(self.errors, [])

    def test_player_does_not_infer_permission_from_absent_or_string_config(self):
        html = self.doodle_export("player-config", False)
        original = html.read_text(encoding="utf-8")
        pattern = r'(<script type="application/json" id="typebit-config">)(.*?)(</script>)'
        match = re.search(pattern, original, flags=re.S)
        self.assertIsNotNone(match)
        for setting in ("omitted", "false"):
            with self.subTest(setting=setting):
                config = json.loads(match.group(2))
                if setting == "omitted":
                    config.pop("doodle", None)
                else:
                    config["doodle"] = setting
                # Exercise the standalone player itself as well as the Python renderer.
                edited = original[:match.start(2)] + json.dumps(config) + original[match.end(2):]
                variant = html.with_name(f"config-{setting}.html")
                variant.write_text(edited, encoding="utf-8")
                self.assert_no_added_doodle_pixels(variant)


if __name__ == "__main__":
    unittest.main()
