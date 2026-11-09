import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1] / 'skills/optimax'
SPEC = importlib.util.spec_from_file_location('install_local', ROOT / 'scripts/install_local.py')
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


def archive(path, extras=(), omit=()):
    with zipfile.ZipFile(path, 'w') as z:
        for name in ('SKILL.md', 'agents/openai.yaml'):
            if name not in omit:
                z.write(ROOT / name, 'optimax/' + name)
        for directory, suffix in (('references', '.md'), ('scripts', '.py')):
            for source in (ROOT / directory).glob('*' + suffix):
                name = str(source.relative_to(ROOT))
                if name not in omit:
                    z.write(source, 'optimax/' + name)
        z.writestr('optimax/model-perf/private.csv', 'private')
        z.writestr('optimax/tests/example.py', 'test')
        for name, data in extras:
            z.writestr(name, data)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.zip = self.base / 'skill.zip'
        self.dest = self.base / 'optimax'
        archive(self.zip)

    def test_install_runtime_and_status(self):
        before = self.zip.read_bytes()
        installer.install(self.zip, self.dest)
        self.assertEqual(before, self.zip.read_bytes())
        self.assertFalse((self.dest / 'model-perf').exists())
        self.assertFalse((self.dest / 'tests').exists())
        self.assertTrue((self.dest / 'scripts/performance.py').is_file())
        run = subprocess.run([sys.executable, str(self.dest / 'scripts/performance.py'), '--root', str(self.base), '--user', 'test', '--session', 'test', 'status'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('"enabled":false', run.stdout.lower())

    def test_existing_and_broken_symlink_are_never_modified(self):
        self.dest.mkdir()
        (self.dest / 'keep').write_text('unchanged')
        with self.assertRaises(FileExistsError): installer.install(self.zip, self.dest)
        self.assertEqual((self.dest / 'keep').read_text(), 'unchanged')
        (self.dest / 'keep').unlink()
        self.dest.rmdir()
        self.dest.symlink_to(self.base / 'missing', target_is_directory=True)
        with self.assertRaises(FileExistsError): installer.install(self.zip, self.dest)
        self.assertTrue(self.dest.is_symlink())

    def test_target_appearing_before_mkdir_is_preserved(self):
        original = Path.mkdir
        def race(path, *args, **kwargs):
            if path == self.dest:
                original(path)
                (path / 'foreign').write_text('safe')
            return original(path, *args, **kwargs)
        with mock.patch.object(Path, 'mkdir', race):
            with self.assertRaises(FileExistsError): installer.install(self.zip, self.dest)
        self.assertEqual((self.dest / 'foreign').read_text(), 'safe')

    def test_missing_parallel_guide_is_rejected_before_creating_destination(self):
        archive(self.zip, omit=('references/parallel-execution.md',))
        with self.assertRaisesRegex(ValueError, 'references/parallel-execution.md'):
            installer.install(self.zip, self.dest)
        self.assertFalse(self.dest.exists())

    def test_malformed_missing_wrong_name_and_unsafe_archives_fail(self):
        for kind in ('malformed', 'missing', 'name', 'traversal', 'symlink', 'duplicate', 'unexpected'):
            with self.subTest(kind=kind):
                if kind == 'malformed': self.zip.write_bytes(b'not a zip')
                elif kind == 'missing': archive(self.zip, omit=('scripts/ladder.py',))
                elif kind == 'name':
                    archive(self.zip, omit=('SKILL.md',), extras=(('optimax/SKILL.md', '---\nname: wrong\n---\n'),))
                elif kind == 'traversal': archive(self.zip, extras=(('optimax/../escape', 'bad'),))
                elif kind == 'duplicate': archive(self.zip, extras=(('optimax/SKILL.md', 'bad'),))
                elif kind == 'unexpected': archive(self.zip, extras=(('optimax/scripts/evil.sh', 'bad'),))
                else:
                    archive(self.zip)
                    with zipfile.ZipFile(self.zip, 'a') as z:
                        info = zipfile.ZipInfo('optimax/scripts/link.py')
                        info.create_system = 3
                        info.external_attr = (0o120777 << 16)
                        z.writestr(info, 'target')
                with self.assertRaises((ValueError, zipfile.BadZipFile)): installer.install(self.zip, self.dest)
                self.assertFalse(self.dest.exists())
                self.assertFalse((self.base / 'escape').exists())

    def test_copy_failure_removes_owned_files_and_preserves_foreign(self):
        original = zipfile.ZipFile.open
        def fail(z, name, *args, **kwargs):
            if self.dest.exists() and isinstance(name, zipfile.ZipInfo) and name.filename.endswith('scripts/ladder.py'):
                (self.dest / 'foreign').write_text('safe')
                raise OSError('copy interrupted')
            return original(z, name, *args, **kwargs)
        with mock.patch.object(zipfile.ZipFile, 'open', fail):
            with self.assertRaisesRegex(OSError, 'incomplete cleanup'): installer.install(self.zip, self.dest)
        self.assertEqual((self.dest / 'foreign').read_text(), 'safe')
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), ['foreign'])

    def test_keyboard_interrupt_removes_partial_install_and_allows_retry(self):
        def interrupt(source, output):
            output.write(b'partial')
            raise KeyboardInterrupt('cancelled')
        with mock.patch.object(installer.shutil, 'copyfileobj', interrupt):
            with self.assertRaisesRegex(KeyboardInterrupt, 'cancelled'):
                installer.install(self.zip, self.dest)
        self.assertFalse(self.dest.exists())
        installer.install(self.zip, self.dest)
        self.assertTrue((self.dest / 'SKILL.md').is_file())

    def test_interrupt_during_root_identity_reports_unknown_ownership(self):
        with mock.patch.object(installer, '_identity', side_effect=KeyboardInterrupt('identity cancelled')):
            with self.assertRaisesRegex(OSError, 'incomplete cleanup') as caught:
                installer.install(self.zip, self.dest)
        self.assertIsInstance(caught.exception.__cause__, KeyboardInterrupt)
        self.assertTrue(self.dest.is_dir())
        self.assertEqual(list(self.dest.iterdir()), [])

    def test_interrupt_during_root_identity_preserves_replacement(self):
        displaced = self.base / 'displaced'
        def replace_then_interrupt(path):
            path.rename(displaced)
            path.mkdir()
            (path / 'foreign').write_text('safe')
            raise KeyboardInterrupt('identity cancelled')
        with mock.patch.object(installer, '_identity', side_effect=replace_then_interrupt):
            with self.assertRaisesRegex(OSError, 'incomplete cleanup') as caught:
                installer.install(self.zip, self.dest)
        self.assertIsInstance(caught.exception.__cause__, KeyboardInterrupt)
        self.assertEqual((self.dest / 'foreign').read_text(), 'safe')
        self.assertTrue(displaced.is_dir())

    def test_interrupt_after_root_mkdir_reports_unknown_ownership(self):
        original = Path.mkdir
        def create_then_interrupt(path, *args, **kwargs):
            original(path, *args, **kwargs)
            raise KeyboardInterrupt('mkdir cancelled')
        with mock.patch.object(Path, 'mkdir', create_then_interrupt):
            with self.assertRaisesRegex(OSError, 'incomplete cleanup') as caught:
                installer.install(self.zip, self.dest)
        self.assertIsInstance(caught.exception.__cause__, KeyboardInterrupt)
        self.assertTrue(self.dest.is_dir())

    def test_interrupt_before_root_mkdir_preserves_original_cancellation(self):
        with mock.patch.object(Path, 'mkdir', side_effect=KeyboardInterrupt('mkdir cancelled')):
            with self.assertRaisesRegex(KeyboardInterrupt, 'mkdir cancelled'):
                installer.install(self.zip, self.dest)
        self.assertFalse(self.dest.exists())

    def test_keyboard_interrupt_reports_incomplete_cleanup_and_preserves_foreign(self):
        def interrupt(source, output):
            output.write(b'partial')
            (self.dest / 'foreign').write_text('safe')
            raise KeyboardInterrupt('cancelled')
        with mock.patch.object(installer.shutil, 'copyfileobj', interrupt):
            with self.assertRaisesRegex(OSError, 'incomplete cleanup') as caught:
                installer.install(self.zip, self.dest)
        self.assertIsInstance(caught.exception.__cause__, KeyboardInterrupt)
        self.assertEqual((self.dest / 'foreign').read_text(), 'safe')
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), ['foreign'])

    def test_cli_installs_to_explicit_destination(self):
        run = subprocess.run([sys.executable, str(ROOT / 'scripts/install_local.py'), '--archive', str(self.zip), '--dest', str(self.dest)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue((self.dest / 'SKILL.md').is_file())


if __name__ == '__main__': unittest.main()
