"""Public entrypoints remain portable while old editable projects still render."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/tracegif'
sys.path.insert(0, str(SKILL / 'scripts'))
from typebitlib import __version__
from typebitlib.core import prepare_project, render_project


class MigrationTests(unittest.TestCase):
    def invoke(self, script, *args, cwd=None):
        result = subprocess.run([sys.executable, str(script), *map(str, args)], cwd=cwd,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_new_and_legacy_entrypoints_report_the_same_runtime(self):
        scripts = [SKILL / 'scripts/tracegif.py', SKILL / 'scripts/typebit.py',
                   ROOT / 'skills/typebit-line-animation/scripts/typebit.py']
        for script in scripts:
            with self.subTest(script=str(script)):
                self.assertEqual(self.invoke(script, '--version').strip(), f'TraceGIF {__version__}')

    def test_copied_skill_can_prepare_and_render_without_the_repository(self):
        with tempfile.TemporaryDirectory(prefix='tracegif-portable-') as folder:
            base = Path(folder)
            copied = base / 'tracegif'
            shutil.copytree(SKILL, copied, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            source = base / 'source.svg'
            source.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 90">'
                              '<path id="roof" d="M20 65 L60 25 L100 65" fill="none" stroke="#245c44"/>'
                              '</svg>', encoding='utf-8')
            project = base / 'project'
            cli = copied / 'scripts/tracegif.py'
            self.assertEqual(json.loads(self.invoke(cli, 'prepare', source, '--project', project, cwd=base))['status'], 'prepared')
            result = json.loads(self.invoke(cli, 'render', project, cwd=base))
            self.assertEqual(result['status'], 'rendered')
            html = (project / 'animation.html').read_text(encoding='utf-8')
            self.assertIn('TraceGIF', html)
            self.assertIn('GIF settings', html)
            self.assertIn('Copyright (c) 2017 Matt DesLauriers', html)

    def test_old_schema_key_and_artwork_survive_the_new_renderer(self):
        with tempfile.TemporaryDirectory(prefix='tracegif-migration-') as folder:
            project = Path(folder) / 'old-project'
            prepare_project(ROOT / 'examples/source/typebit-mark.svg', project)
            config_path = project / 'project.json'
            config = json.loads(config_path.read_text(encoding='utf-8'))
            config['typebit_version'] = '0.3.0'
            config_path.write_text(json.dumps(config), encoding='utf-8')
            originals = {name: (project / name).read_bytes() for name in ['scene.svg', config['source']['path']]}
            rendered = render_project(project)
            updated = json.loads(config_path.read_text(encoding='utf-8'))
            self.assertEqual(updated['typebit_version'], __version__)
            self.assertEqual(updated['source'], config['source'])
            self.assertEqual(updated['layers'], config['layers'])
            for name, payload in originals.items():
                self.assertEqual((project / name).read_bytes(), payload)
            self.assertEqual(updated['render']['html_sha256'], rendered['html_sha256'])


if __name__ == '__main__':
    unittest.main()
