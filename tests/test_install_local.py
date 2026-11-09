import importlib.util
import lzma
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1] / 'skills/optimax'
SPEC = importlib.util.spec_from_file_location('install_local', ROOT / 'scripts/install_local.py')
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


def archive(path, extras=(), omit=(), compression=zipfile.ZIP_STORED):
    with zipfile.ZipFile(path, 'w', compression=compression) as z:
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

    def test_missing_instruction_audit_is_rejected_before_creating_destination(self):
        archive(self.zip, omit=('scripts/instruction_audit.py',))
        with self.assertRaisesRegex(ValueError, 'scripts/instruction_audit.py'):
            installer.install(self.zip, self.dest)
        self.assertFalse(self.dest.exists())

    def test_invalid_skill_frontmatter_is_rejected_before_destination_creation(self):
        cases = {
            'unclosed': '---\nname: optimax\ndescription: Useful skill\n',
            'missing description': '---\nname: optimax\n---\nBody\n',
            'blank description': '---\nname: optimax\ndescription:   \n---\nBody\n',
            'name in body': '---\ndescription: Useful skill\n---\nname: optimax\n',
            'description in body': '---\nname: optimax\n---\ndescription: Useful skill\n',
            'quoted empty': '---\nname: optimax\ndescription: ""\n---\n',
            'null': '---\nname: optimax\ndescription: null\n---\n',
            'boolean': '---\nname: optimax\ndescription: true\n---\n',
            'block': '---\nname: optimax\ndescription: >\n  Useful skill\n---\n',
            'duplicate name': '---\nname: optimax\nname: optimax\ndescription: Useful skill\n---\n',
            'duplicate description': '---\nname: optimax\ndescription: One\ndescription: Two\n---\n',
        }
        for index, (case, skill) in enumerate(cases.items()):
            with self.subTest(case=case):
                dest = self.base / f'invalid-{index}'
                archive(self.zip, omit=('SKILL.md',), extras=(('optimax/SKILL.md', skill),))
                with self.assertRaises(ValueError):
                    installer.install(self.zip, dest)
                self.assertFalse(dest.exists())

    def test_canonical_skill_frontmatter_accepts_lf_and_crlf(self):
        skill = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        for newline in ('\n', '\r\n'):
            with self.subTest(newline=repr(newline)):
                dest = self.base / ('lf' if newline == '\n' else 'crlf')
                archive(self.zip, omit=('SKILL.md',), extras=(('optimax/SKILL.md', skill.replace('\n', newline)),))
                installer.install(self.zip, dest)
                self.assertTrue((dest / 'SKILL.md').is_file())

    def test_plain_description_must_be_a_string(self):
        for index, value in enumerate(('yes', 'NO', 'on', 'Off', '123', '-1.5', '0xFF', '.nan', '.Inf', '2026-11-09', '*alias')):
            with self.subTest(value=value):
                dest = self.base / f'nonstring-{index}'
                skill = f'---\nname: optimax\ndescription: {value}\n---\n'
                archive(self.zip, omit=('SKILL.md',), extras=(('optimax/SKILL.md', skill),))
                with self.assertRaises(ValueError):
                    installer.install(self.zip, dest)
                self.assertFalse(dest.exists())

    def test_plain_description_accepts_ordinary_text(self):
        for index, value in enumerate(('Café & tea.', '123 useful tools!', 'yes, a useful skill', 'v1.2', '日本語の説明')):
            with self.subTest(value=value):
                dest = self.base / f'text-{index}'
                skill = f'---\nname: optimax\ndescription: {value}\n---\n'
                archive(self.zip, omit=('SKILL.md',), extras=(('optimax/SKILL.md', skill),))
                installer.install(self.zip, dest)
                self.assertTrue((dest / 'SKILL.md').is_file())

    def test_plain_description_rejects_yaml_syntax_before_destination_creation(self):
        values = ('-', '?', ':', '=', '<<', '- item', '? item',
                  'foo:\tbar', 'foo:', 'foo\t# note', 'nul\x00text')
        for index, value in enumerate(values):
            with self.subTest(value=repr(value)):
                dest = self.base / f'bad-plain-{index}'
                skill = f'---\nname: optimax\ndescription: {value}\n---\n'
                archive(self.zip, omit=('SKILL.md',), extras=(('optimax/SKILL.md', skill),))
                with self.assertRaises(ValueError):
                    installer.install(self.zip, dest)
                self.assertFalse(dest.exists())

    def test_plain_description_accepts_yaml_safe_punctuation(self):
        for index, value in enumerate(('-fast', '?question', 'x:y', 'a#b', '日本語', '123 useful')):
            with self.subTest(value=value):
                dest = self.base / f'safe-plain-{index}'
                skill = f'---\nname: optimax\ndescription: {value}\n---\n'
                archive(self.zip, omit=('SKILL.md',), extras=(('optimax/SKILL.md', skill),))
                installer.install(self.zip, dest)
                self.assertTrue((dest / 'SKILL.md').is_file())

    def test_raw_frontmatter_rejects_tabs_and_controls_before_install(self):
        headers = ('name:\toptimax\ndescription: Useful',
                   'name: optimax\tdescription\ndescription: Useful',
                   'name: optimax\ndescription:\tUseful',
                   'name: optimax\ndescription: Useful\ttool',
                   'name: optimax\ndescription: Useful\x1f')
        for index, header in enumerate(headers):
            with self.subTest(header=repr(header)):
                dest = self.base / f'bad-control-{index}'
                archive(self.zip, omit=('SKILL.md',), extras=(('optimax/SKILL.md', f'---\n{header}\n---\n'),))
                with self.assertRaises(ValueError):
                    installer.install(self.zip, dest)
                self.assertFalse(dest.exists())

    def test_frontmatter_requires_space_after_field_colon(self):
        headers = ('name:optimax\ndescription: Useful',
                   'name: optimax\ndescription:Useful')
        for index, header in enumerate(headers):
            with self.subTest(header=header):
                dest = self.base / f'no-separator-{index}'
                archive(self.zip, omit=('SKILL.md',), extras=(('optimax/SKILL.md', f'---\n{header}\n---\n'),))
                with self.assertRaises(ValueError):
                    installer.install(self.zip, dest)
                self.assertFalse(dest.exists())

    def test_plain_description_preserves_non_ascii_space(self):
        for index, value in enumerate(('a:\u00a0b', 'a\u00a0#b', '-\u00a0word', '日本語', '\u00a0null', 'null\u00a0')):
            with self.subTest(value=value):
                dest = self.base / f'non-ascii-space-{index}'
                skill = f'---\nname: optimax\ndescription: {value}\n---\n'
                archive(self.zip, omit=('SKILL.md',), extras=(('optimax/SKILL.md', skill),))
                installer.install(self.zip, dest)
                self.assertEqual((dest / 'SKILL.md').read_text(encoding='utf-8'), skill)

    def test_name_with_non_ascii_space_is_not_optimax(self):
        for index, name in enumerate(('\u00a0optimax', 'optimax\u00a0')):
            with self.subTest(name=name):
                dest = self.base / f'bad-name-space-{index}'
                skill = f'---\nname: {name}\ndescription: Useful\n---\n'
                archive(self.zip, omit=('SKILL.md',), extras=(('optimax/SKILL.md', skill),))
                with self.assertRaises(ValueError):
                    installer.install(self.zip, dest)
                self.assertFalse(dest.exists())

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

    def test_cli_reports_corrupt_compressed_members_without_traceback(self):
        cases = ((zipfile.ZIP_DEFLATED, 0, zlib.error),
                 (zipfile.ZIP_LZMA, 9, lzma.LZMAError))
        for compression, offset, error in cases:
            for member in ('SKILL.md', 'scripts/ladder.py'):
                with self.subTest(compression=compression, member=member):
                    self._assert_corrupt_member_failure(compression, offset, error, member)

    def _assert_corrupt_member_failure(self, compression, offset, error, member):
        archive(self.zip, compression=compression)
        with zipfile.ZipFile(self.zip) as z:
            self.assertIsNone(z.testzip())
            info = z.getinfo('optimax/' + member)
        data = bytearray(self.zip.read_bytes())
        name_length, extra_length = struct.unpack_from('<HH', data, info.header_offset + 26)
        payload_offset = info.header_offset + 30 + name_length + extra_length
        # Invalidate the DEFLATE block type or LZMA range-coded data.
        data[payload_offset + offset] = 0xff
        self.zip.write_bytes(data)
        with zipfile.ZipFile(self.zip) as z:
            with self.assertRaises(error):
                z.read(info.filename)
        run = subprocess.run([sys.executable, str(ROOT / 'scripts/install_local.py'), '--archive', str(self.zip), '--dest', str(self.dest)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertFalse(self.dest.exists())
        self.assertTrue(run.stderr.startswith('installation failed:'), run.stderr)
        self.assertNotIn('Traceback', run.stderr)
        self.assertEqual(run.stdout, '')

    def test_cli_reports_unreadable_required_skill_without_traceback(self):
        for kind in ('encrypted', 'unsupported compression'):
            with self.subTest(kind=kind):
                archive(self.zip)
                data = bytearray(self.zip.read_bytes())
                central = data.index(b'PK\x01\x02')
                # SKILL.md is the first entry: alter its local and central headers.
                if kind == 'encrypted':
                    struct.pack_into('<H', data, 6, 1)
                    struct.pack_into('<H', data, central + 8, 1)
                else:
                    struct.pack_into('<H', data, 8, 99)
                    struct.pack_into('<H', data, central + 10, 99)
                self.zip.write_bytes(data)
                run = subprocess.run([sys.executable, str(ROOT / 'scripts/install_local.py'), '--archive', str(self.zip), '--dest', str(self.dest)], capture_output=True, text=True)
                self.assertEqual(run.returncode, 1)
                self.assertTrue(run.stderr.startswith('installation failed:'), run.stderr)
                self.assertNotIn('Traceback', run.stderr)
                self.assertFalse(self.dest.exists())


if __name__ == '__main__': unittest.main()
