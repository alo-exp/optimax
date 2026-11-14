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
    def test_plugin_only_build_has_no_installer_dependency_or_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source'
            shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns('.git', 'dist', '__pycache__'))
            installer = source / 'skills/optimax/scripts/install_local.py'
            if installer.exists():
                installer.unlink()
            output = Path(tmp) / 'output'
            result = subprocess.run([sys.executable, str(source / 'build_release.py'), '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual([path.name for path in output.iterdir()], ['optimax-plugin.zip'])
            with zipfile.ZipFile(output / 'optimax-plugin.zip') as plugin:
                self.assertIn('skills/optimax/SKILL.md', plugin.namelist())
                self.assertIn('skills/review-ladder/SKILL.md', plugin.namelist())
                self.assertFalse(any('install_local' in name for name in plugin.namelist()))

    def test_release_outputs_only_plugin_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(ROOT / 'build_release.py'), '--output', tmp], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(sorted(path.name for path in Path(tmp).iterdir()), ['optimax-plugin.zip'])

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

    def test_invalid_optimax_frontmatter_preserves_published_archives(self):
        headers = (
            '---\nname: optimax\n---\n# No description\n',
            '---\nname: optimax\ndescription: \n---\n',
            '---\nname: optimax\ndescription: [invalid]\n---\n',
            '---\nname: optimax\ndescription: valid\n',
        )
        for header in headers:
            with self.subTest(header=header), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve() / 'source'
                builder, _ = self.release_fixture(root)
                output = Path(tmp) / 'output'
                with patch.object(builder, 'ROOT', root), patch.object(builder, 'RUNTIME', root / 'skills/optimax'):
                    builder.build(output)
                    names = ('optimax-plugin.zip',)
                    previous = {name: (output / name).read_bytes() for name in names}
                    (root / 'skills/optimax/SKILL.md').write_text(header)
                    with self.assertRaises(ValueError):
                        builder.build(output)
                self.assertEqual({name: (output / name).read_bytes() for name in names}, previous)
                self.assertEqual(sorted(path.name for path in output.iterdir()), sorted(names))

    def test_invalid_review_ladder_frontmatter_preserves_published_archives(self):
        headers = (
            'broken frontmatter\n',
            '---\nname: optimax\ndescription: valid\n---\n',
            '---\nname: review-ladder\n---\n',
            '---\nname: review-ladder\ndescription: [invalid]\n---\n',
            '---\nname: review-ladder\ndescription: valid\n',
        )
        for header in headers:
            with self.subTest(header=header), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve() / 'source'
                builder, _ = self.release_fixture(root)
                output = Path(tmp) / 'output'
                with patch.object(builder, 'ROOT', root), patch.object(builder, 'RUNTIME', root / 'skills/optimax'):
                    builder.build(output)
                    names = ('optimax-plugin.zip',)
                    previous = {name: (output / name).read_bytes() for name in names}
                    (root / 'skills/review-ladder/SKILL.md').write_text(header)
                    with self.assertRaises(ValueError):
                        builder.build(output)
                self.assertEqual({name: (output / name).read_bytes() for name in names}, previous)
                self.assertEqual(sorted(path.name for path in output.iterdir()), sorted(names))

    def test_yaml12_octal_descriptions_preserve_published_archives(self):
        for skill in ('optimax', 'review-ladder'):
            for description in ('0o12', '0o0', '0o07', '0o777'):
                with self.subTest(skill=skill, description=description), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp).resolve() / 'source'
                    builder, _ = self.release_fixture(root)
                    output = Path(tmp) / 'output'
                    with patch.object(builder, 'ROOT', root), patch.object(builder, 'RUNTIME', root / 'skills/optimax'):
                        builder.build(output)
                        previous = (output / 'optimax-plugin.zip').read_bytes()
                        (root / f'skills/{skill}/SKILL.md').write_text(
                            f'---\nname: {skill}\ndescription: {description}\n---\n')
                        with self.assertRaisesRegex(ValueError, 'nonempty plain description'):
                            builder.build(output)
                    self.assertEqual((output / 'optimax-plugin.zip').read_bytes(), previous)
                    self.assertEqual(sorted(path.name for path in output.iterdir()), ['optimax-plugin.zip'])

    def test_octal_looking_string_descriptions_preserve_plain_scalar_contract(self):
        for skill in ('optimax', 'review-ladder'):
            for description in ('0O12', '+0o12', '-0o12', '0o7_1', '0o_12', '0o128', '0o'):
                with self.subTest(skill=skill, description=description), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp).resolve() / 'source'
                    builder, _ = self.release_fixture(root)
                    (root / f'skills/{skill}/SKILL.md').write_text(
                        f'---\nname: {skill}\ndescription: {description}\n---\n')
                    output = Path(tmp) / 'output'
                    with patch.object(builder, 'ROOT', root), patch.object(builder, 'RUNTIME', root / 'skills/optimax'):
                        builder.build(output)
                    with zipfile.ZipFile(output / 'optimax-plugin.zip') as plugin:
                        self.assertEqual(plugin.read(f'skills/{skill}/SKILL.md'),
                                         (root / f'skills/{skill}/SKILL.md').read_bytes())

    def test_quoted_numeric_descriptions_remain_outside_plain_scalar_contract(self):
        for skill in ('optimax', 'review-ladder'):
            for description in ('"0o12"', "'0o12'"):
                with self.subTest(skill=skill, description=description), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp).resolve() / 'source'
                    builder, _ = self.release_fixture(root)
                    (root / f'skills/{skill}/SKILL.md').write_text(
                        f'---\nname: {skill}\ndescription: {description}\n---\n')
                    with patch.object(builder, 'ROOT', root), patch.object(builder, 'RUNTIME', root / 'skills/optimax'):
                        with self.assertRaisesRegex(ValueError, 'nonempty plain description'):
                            builder.build(Path(tmp) / 'output')

    def test_plugin_bundles_review_ladder_exactly(self):
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
                original = {name: (output / name).read_bytes() for name in ('optimax-plugin.zip',)}
                builder.build(output)
            self.assertEqual(original, {name: (output / name).read_bytes() for name in original})
            with zipfile.ZipFile(output / 'optimax-plugin.zip') as plugin:
                expected_review = {'skills/review-ladder/' + name for name in review_files}
                self.assertEqual({name for name in plugin.namelist() if name.startswith('skills/review-ladder/')}, expected_review)
                expected_plugin = {'LICENSE', *builder.MANIFESTS,
                                   *('skills/optimax/' + name for name in builder.FILES), *expected_review}
                self.assertEqual(set(plugin.namelist()), expected_plugin)
                for relative in expected_review:
                    self.assertEqual(plugin.read(relative), (root / relative).read_bytes())
                self.assertEqual(json.loads(plugin.read('.codex-plugin/plugin.json'))['skills'], './skills/')
                self.assertIn(b'name: review-ladder', plugin.read('skills/review-ladder/SKILL.md'))
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
                for name in ('optimax-plugin.zip',):
                    (output / name).write_bytes(b'previous')
                with patch.object(builder, 'ROOT', root), patch.object(builder, 'RUNTIME', root / 'skills/optimax'):
                    with self.assertRaisesRegex(ValueError, 'symlink'):
                        builder.build(output)
                self.assertEqual([(output / name).read_bytes() for name in ('optimax-plugin.zip',)], [b'previous'])
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

    def test_packaged_plugin_homepages_point_to_live_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            build = subprocess.run([sys.executable, str(ROOT / 'build_release.py'), '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            with zipfile.ZipFile(output / 'optimax-plugin.zip') as plugin:
                for name in ('plugin.json', '.claude-plugin/plugin.json'):
                    with self.subTest(manifest=name):
                        self.assertEqual(json.loads(plugin.read(name))['homepage'], 'https://alo-exp.github.io/optimax/')

    def test_candidate_release_archive_identifies_0_2_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            build = subprocess.run([sys.executable, str(ROOT / 'build_release.py'), '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            with zipfile.ZipFile(output / 'optimax-plugin.zip') as plugin:
                for name in ('plugin.json', '.codex-plugin/plugin.json', '.claude-plugin/plugin.json'):
                    with self.subTest(manifest=name):
                        self.assertEqual(json.loads(plugin.read(name))['version'], '0.2.0')
            self.assertRegex((ROOT / 'CHANGELOG.md').read_text(encoding='utf-8'), r'\A# Changelog\n\n## 0\.2\.0 \(prerelease\)')

    def test_release_archives_include_instruction_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            build = subprocess.run([sys.executable, str(ROOT / 'build_release.py'), '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            for archive, member in (('optimax-plugin.zip', 'skills/optimax/scripts/instruction_audit.py'),):
                with self.subTest(archive=archive), zipfile.ZipFile(output / archive) as z:
                    self.assertEqual(z.read(member), (RUNTIME / 'scripts/instruction_audit.py').read_bytes())

    def test_release_archives_match_current_changelog_and_runtime_sources(self):
        release = re.search(r'^## (\d+\.\d+\.\d+)(?:\s|$)', (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8'), re.MULTILINE)
        self.assertIsNotNone(release, 'changelog must identify the current release')
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            build = subprocess.run([sys.executable, str(ROOT / 'build_release.py'), '--output', str(out)], capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            with zipfile.ZipFile(out / 'optimax-plugin.zip') as plugin:
                for name in ('plugin.json', '.codex-plugin/plugin.json', '.claude-plugin/plugin.json'):
                    with self.subTest(manifest=name):
                        archived = plugin.read(name)
                        self.assertEqual(archived, (ROOT / name).read_bytes())
                        self.assertEqual(json.loads(archived)['version'], release.group(1))
                for name in plugin.namelist():
                    with self.subTest(source=name):
                        self.assertEqual(plugin.read(name), (ROOT / name).read_bytes())
            status = subprocess.run([sys.executable, str(RUNTIME / 'scripts/performance.py'), '--root', str(out), '--user', 'release-test', '--session', 'release-test', 'status'], capture_output=True, text=True)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIs(json.loads(status.stdout)['enabled'], False)

    def test_builder_is_deterministic_and_excludes_private_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            cmd = [sys.executable, str(ROOT / 'build_release.py'), '--output', str(out)]
            first = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            plugin = out / 'optimax-plugin.zip'
            original = plugin.read_bytes()
            second = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(original, plugin.read_bytes())
            with zipfile.ZipFile(plugin) as z:
                names = set(z.namelist())
                self.assertIn('LICENSE', names)
                self.assertIn('plugin.json', names)
                self.assertIn('.claude-plugin/plugin.json', names)
                self.assertIn('skills/optimax/SKILL.md', names)
                self.assertIn('skills/review-ladder/SKILL.md', names)
                self.assertFalse(any('model-perf' in n or '__pycache__' in n for n in names))


if __name__ == '__main__':
    unittest.main()
