import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'skills/optimax'


class OptimaxPackagingTests(unittest.TestCase):
    def test_manifests_credit_author_and_alo_labs(self):
        for name in ('plugin.json', '.codex-plugin/plugin.json', '.claude-plugin/plugin.json'):
            with self.subTest(manifest=name):
                manifest = json.loads((ROOT / name).read_text(encoding='utf-8'))
                self.assertEqual(manifest['author']['name'], 'Shafqat Ullah')
                self.assertIn('Ālo Labs', manifest['description'])

    def test_installer_accepts_optimax_archive_and_default_destination(self):
        spec = importlib.util.spec_from_file_location('installer', RUNTIME / 'scripts/install_local.py')
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / 'skill.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                for rel in sorted(installer.REQUIRED):
                    data = (RUNTIME / rel).read_bytes()
                    if rel == 'SKILL.md':
                        data = data.replace(b'name: optimal-ultra', b'name: optimax', 1)
                    z.writestr('optimax/' + rel, data)
            dest = Path(tmp) / 'installed'
            installer.install(archive, dest)
            self.assertTrue((dest / 'scripts/performance.py').is_file())
            home = Path(tmp) / 'home'
            (home / '.codex/skills').mkdir(parents=True)
            result = subprocess.run([sys.executable, str(RUNTIME / 'scripts/install_local.py'), '--archive', str(archive)], env={**os.environ, 'HOME': str(home)}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((home / '.codex/skills/optimax/SKILL.md').is_file())

    def test_builder_is_deterministic_and_excludes_private_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            cmd = [sys.executable, str(ROOT / 'build_release.py'), '--output', str(out)]
            first = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            skill = out / 'optimax-skill.zip'
            plugin = out / 'optimax-plugin.zip'
            installed = out / 'installed'
            install = subprocess.run([sys.executable, str(RUNTIME / 'scripts/install_local.py'), '--archive', str(skill), '--dest', str(installed)], capture_output=True, text=True)
            self.assertEqual(install.returncode, 0, install.stderr)
            self.assertEqual((installed / 'LICENSE').read_bytes(), (ROOT / 'LICENSE').read_bytes())
            originals = [p.read_bytes() for p in (skill, plugin)]
            second = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(originals, [p.read_bytes() for p in (skill, plugin)])
            with zipfile.ZipFile(skill) as z:
                names = set(z.namelist())
                self.assertIn('optimax/SKILL.md', names)
                self.assertIn('optimax/scripts/performance.py', names)
                self.assertIn('optimax/LICENSE', names)
                self.assertFalse(any('model-perf' in n or '__pycache__' in n for n in names))
            with zipfile.ZipFile(plugin) as z:
                names = set(z.namelist())
                self.assertIn('LICENSE', names)
                self.assertIn('plugin.json', names)
                self.assertIn('.claude-plugin/plugin.json', names)
                self.assertIn('skills/optimax/SKILL.md', names)
                self.assertFalse(any('model-perf' in n or '__pycache__' in n for n in names))


if __name__ == '__main__':
    unittest.main()
