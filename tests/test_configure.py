"""Project revisions keep artwork stable while changing delivery timing."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/typebit-line-animation/scripts'))
from typebitlib.core import (TypeBitError, configure_project, prepare_project,
                             render_project, require_current_render, package_project)


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='typebit-configure-')
        self.base = Path(self.temp.name)
        source = self.base / 'source.svg'
        source.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path id="a" d="M20 20H80V80H20Z" fill="#894c27"/><path id="b" data-phase="details" d="M30 30L70 70" stroke="black"/></svg>', encoding='utf-8')
        self.project = self.base / 'project'
        prepare_project(source, self.project)
        render_project(self.project)

    def tearDown(self):
        self.temp.cleanup()

    def manifest(self):
        return json.loads((self.project / 'project.json').read_text(encoding='utf-8'))

    def test_retime_preserves_artwork_layer_identity_and_previous_render(self):
        before = self.manifest()
        scene = (self.project / 'scene.svg').read_bytes()
        previous_html = (self.project / 'animation.html').read_bytes()
        result = configure_project(self.project, duration=20, playback_rate=1.25)
        after = self.manifest()
        self.assertEqual(result['effective_duration'], 16)
        self.assertEqual(after['fill_start'], before['fill_start'] * 2)
        for old, new in zip(before['layers'], after['layers']):
            self.assertEqual(old['id'], new['id'])
            self.assertEqual(new['start'], old['start'] * 2)
            self.assertEqual(new['duration'], old['duration'] * 2)
        self.assertEqual((self.project / 'scene.svg').read_bytes(), scene)
        with self.assertRaises(TypeBitError):
            require_current_render(self.project)
        render_project(self.project)
        require_current_render(self.project)
        with zipfile.ZipFile(self.project / 'revisions/r0001.zip') as old:
            self.assertEqual(old.read('animation.html'), previous_html)

    def test_invalid_configuration_does_not_partially_change_project(self):
        path = self.project / 'project.json'
        before = path.read_bytes()
        for options in ({}, {'duration': 0}, {'duration': float('nan')},
                        {'playback_rate': 5}, {'playback_rate': True},
                        {'duration': 20, 'playback_rate': 0}, {'doodle': 'off'}):
            with self.subTest(options=options), self.assertRaises(TypeBitError):
                configure_project(self.project, **options)
            self.assertEqual(path.read_bytes(), before)

    def test_existing_invalid_rate_and_unrenderable_retiming_are_rejected_atomically(self):
        path = self.project / 'project.json'
        original = self.manifest()
        cases = [
            ({**original, 'playback_rate': 0}, {'doodle': True}),
            ({**original, 'fill_start': 9.999}, {'duration': 1}),
        ]
        for manifest, options in cases:
            with self.subTest(options=options):
                path.write_text(json.dumps(manifest), encoding='utf-8')
                before = path.read_bytes()
                with self.assertRaises(TypeBitError):
                    configure_project(self.project, **options)
                self.assertEqual(path.read_bytes(), before, 'A rejected configuration must not change the saved project')

    def test_revision_archive_cannot_follow_link_outside_project(self):
        outside = self.base / 'outside-project'
        outside.mkdir()
        (outside / 'sentinel.txt').write_text('preserve', encoding='utf-8')
        self.assertTrue(outside.resolve().is_relative_to(self.base.resolve()))
        self.assertFalse(outside.resolve().is_relative_to(self.project.resolve()))
        for folder in ('preview', 'exports', 'verification'):
            directory = self.project / folder
            directory.mkdir()
            (directory / 'sample.txt').write_text('current', encoding='utf-8')
        before = {name: (self.project / name).read_bytes()
                  for name in ('project.json', 'animation.html', '.last-render.zip')}
        link = self.project / 'revisions'
        if os.name == 'nt':
            quote = lambda value: "'" + str(value).replace("'", "''") + "'"
            command = f"New-Item -ItemType Junction -Path {quote(link)} -Target {quote(outside)} | Out-Null"
            try:
                result = subprocess.run(['powershell', '-NoProfile', '-Command', command],
                                        capture_output=True, text=True, timeout=15)
            except (OSError, subprocess.TimeoutExpired) as exc:
                self.skipTest(f'Junction setup unavailable: {exc}')
            if result.returncode:
                self.skipTest('Junction creation is unavailable in this environment')
            self.assertTrue(link.is_junction())
        else:
            link.symlink_to(outside, target_is_directory=True)
        try:
            with self.assertRaises(TypeBitError):
                render_project(self.project)
            self.assertEqual({path.name for path in outside.iterdir()}, {'sentinel.txt'})
            self.assertEqual((outside / 'sentinel.txt').read_text(encoding='utf-8'), 'preserve')
            for name, content in before.items():
                self.assertEqual((self.project / name).read_bytes(), content)
            for folder in ('preview', 'exports', 'verification'):
                self.assertEqual((self.project / folder / 'sample.txt').read_text(encoding='utf-8'), 'current')
        finally:
            # Remove only the directory link itself; the target belongs to this fixture.
            if os.name == 'nt':
                link.rmdir()
            else:
                link.unlink()

    def test_derived_files_can_be_regenerated_and_are_archived_on_rerender(self):
        for folder in ('preview', 'exports', 'verification'):
            directory = self.project / folder
            directory.mkdir()
            (directory / 'sample.txt').write_text('first', encoding='utf-8')
        render_project(self.project)
        for folder in ('preview', 'exports', 'verification'):
            self.assertEqual((self.project / f'revisions/r0001-{folder}/sample.txt').read_text(), 'first')
            directory = self.project / folder
            directory.mkdir()
            (directory / 'sample.txt').write_text('second', encoding='utf-8')
        result = package_project(self.project)
        with zipfile.ZipFile(result['zip']) as archive:
            self.assertEqual(archive.read('exports/sample.txt'), b'second')
        (self.project / 'preview/sample.txt').write_text('updated preview', encoding='utf-8')
        package_project(self.project)

    def test_new_renderer_upgrades_existing_project_version(self):
        path = self.project / 'project.json'
        old = self.manifest()
        old['typebit_version'] = '0.1.0'
        old.pop('playback_rate', None)
        path.write_text(json.dumps(old), encoding='utf-8')
        with self.assertRaisesRegex(TypeBitError, 'current TypeBit'):
            require_current_render(self.project)
        render_project(self.project)
        current = require_current_render(self.project)
        self.assertEqual(current['typebit_version'], '0.2.0')


if __name__ == '__main__':
    unittest.main()
