import importlib.util
import json
import os
from pathlib import Path
import re
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

    def test_release_archives_match_current_changelog_and_runtime_sources(self):
        release = re.search(r'^## (\d+\.\d+\.\d+)(?:\s|$)', (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8'), re.MULTILINE)
        self.assertIsNotNone(release, 'changelog must identify the current release')
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            build = subprocess.run([sys.executable, str(ROOT / 'build_release.py'), '--output', str(out)], capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            with zipfile.ZipFile(out / 'optimax-plugin.zip') as plugin, zipfile.ZipFile(out / 'optimax-skill.zip') as skill:
                for name in ('plugin.json', '.codex-plugin/plugin.json', '.claude-plugin/plugin.json'):
                    with self.subTest(manifest=name):
                        archived = plugin.read(name)
                        self.assertEqual(archived, (ROOT / name).read_bytes())
                        self.assertEqual(json.loads(archived)['version'], release.group(1), 'archive manifest must identify the current changelog release')
                for name in skill.namelist():
                    relative = name.removeprefix('optimax/')
                    source = ROOT / 'LICENSE' if relative == 'LICENSE' else RUNTIME / relative
                    with self.subTest(runtime=relative):
                        self.assertEqual(skill.read(name), source.read_bytes())
                        plugin_name = 'LICENSE' if relative == 'LICENSE' else 'skills/optimax/' + relative
                        self.assertEqual(plugin.read(plugin_name), skill.read(name))
                installed = out / 'installed'
                install = subprocess.run([sys.executable, str(RUNTIME / 'scripts/install_local.py'), '--archive', str(out / 'optimax-skill.zip'), '--dest', str(installed)], capture_output=True, text=True)
                self.assertEqual(install.returncode, 0, install.stderr)
                for name in skill.namelist():
                    with self.subTest(installed=name):
                        self.assertEqual((installed / name.removeprefix('optimax/')).read_bytes(), skill.read(name))
            status = subprocess.run([sys.executable, str(installed / 'scripts/performance.py'), '--root', str(out), '--user', 'release-test', '--session', 'release-test', 'status'], capture_output=True, text=True)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIs(json.loads(status.stdout)['enabled'], False)

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
            result = subprocess.run([sys.executable, str(RUNTIME / 'scripts/install_local.py'), '--archive', str(archive)], env={**os.environ, 'HOME': str(home), 'USERPROFILE': str(home)}, capture_output=True, text=True)
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
