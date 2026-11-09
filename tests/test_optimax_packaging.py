import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
from unittest.mock import patch
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'skills/optimax'


class OptimaxPackagingTests(unittest.TestCase):
    def release_fixture(self, root):
        spec = importlib.util.spec_from_file_location('packaging_builder', ROOT / 'build_release.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        review_files = ('SKILL.md', 'agents/openai.yaml', 'references/report-template.md')
        for relative in ('LICENSE', *builder.MANIFESTS,
                         *('skills/optimax/' + name for name in builder.FILES),
                         *('skills/review-ladder/' + name for name in review_files)):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        return builder, review_files

    def test_plugin_bundles_review_ladder_exactly_without_changing_standalone(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve() / 'source'
            builder, review_files = self.release_fixture(root)
            sentinels = ('model-perf/private.json', 'subagent-model-scores.csv',
                         'skills/review-ladder/tests/test_private.py',
                         'skills/review-ladder/__pycache__/secret.pyc',
                         'skills/review-ladder/session-report.md',
                         'skills/review-ladder/references/unlisted.md')
            for relative in sentinels:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'DISPOSABLE PRIVATE SENTINEL')
            output = Path(tmp) / 'output'
            with patch.object(builder, 'ROOT', root), patch.object(builder, 'RUNTIME', root / 'skills/optimax'):
                builder.build(output)
                original = {name: (output / name).read_bytes() for name in ('optimax-skill.zip', 'optimax-plugin.zip')}
                builder.build(output)
            self.assertEqual(original, {name: (output / name).read_bytes() for name in original})
            with zipfile.ZipFile(output / 'optimax-plugin.zip') as plugin, zipfile.ZipFile(output / 'optimax-skill.zip') as standalone:
                expected_review = {'skills/review-ladder/' + name for name in review_files}
                self.assertEqual({name for name in plugin.namelist() if name.startswith('skills/review-ladder/')}, expected_review)
                expected_plugin = {'LICENSE', *builder.MANIFESTS,
                                   *('skills/optimax/' + name for name in builder.FILES), *expected_review}
                self.assertEqual(set(plugin.namelist()), expected_plugin)
                for relative in expected_review:
                    self.assertEqual(plugin.read(relative), (root / relative).read_bytes())
                self.assertEqual(json.loads(plugin.read('.codex-plugin/plugin.json'))['skills'], './skills/')
                self.assertIn(b'name: review-ladder', plugin.read('skills/review-ladder/SKILL.md'))
                self.assertEqual(set(standalone.namelist()), {'optimax/LICENSE', *('optimax/' + name for name in builder.FILES)})
                self.assertFalse(any(b'DISPOSABLE PRIVATE SENTINEL' in plugin.read(name) for name in plugin.namelist()))

    def test_review_ladder_unsafe_or_missing_sources_fail_before_publication(self):
        for relative in ('skills/review-ladder/SKILL.md', 'skills/review-ladder/agents/openai.yaml',
                         'skills/review-ladder/references/report-template.md', 'skills/review-ladder',
                         'skills/review-ladder/agents', 'skills'):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve() / 'source'
                builder, _ = self.release_fixture(root)
                path = root / relative
                target = Path(tmp) / 'foreign'
                path.rename(target)
                path.symlink_to(target, target_is_directory=target.is_dir())
                output = Path(tmp) / 'output'
                output.mkdir()
                for name in ('optimax-skill.zip', 'optimax-plugin.zip'):
                    (output / name).write_bytes(b'previous')
                with patch.object(builder, 'ROOT', root), patch.object(builder, 'RUNTIME', root / 'skills/optimax'):
                    with self.assertRaisesRegex(ValueError, 'symlink'):
                        builder.build(output)
                self.assertEqual([(output / name).read_bytes() for name in ('optimax-skill.zip', 'optimax-plugin.zip')], [b'previous', b'previous'])
        for kind in ('missing', 'directory'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve() / 'source'
                builder, _ = self.release_fixture(root)
                path = root / 'skills/review-ladder/agents/openai.yaml'
                path.unlink()
                if kind == 'directory':
                    path.mkdir()
                with patch.object(builder, 'ROOT', root), patch.object(builder, 'RUNTIME', root / 'skills/optimax'):
                    with self.assertRaisesRegex(ValueError, 'missing release file'):
                        builder.build(Path(tmp) / 'output')

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
