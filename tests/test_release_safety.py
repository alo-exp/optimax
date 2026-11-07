"""Failure safety for real release archives and promotion."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('release_safety_builder', ROOT / 'build_release.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
NAMES = ('optimax-skill.zip', 'optimax-plugin.zip')


class ReleaseSafetyTests(unittest.TestCase):
    def snapshot(self, output):
        return {name: (output / name).read_bytes() for name in NAMES}

    def previous_release(self, output):
        builder.build(output)
        # Real, valid older archives must differ from the next candidate so a
        # missing rollback cannot accidentally pass a deterministic-build test.
        for name in NAMES:
            with zipfile.ZipFile(output / name, 'a') as archive:
                archive.writestr('previous-version.txt', b'previous release')
        return self.snapshot(output)

    def test_existing_destination_directory_preserves_previous_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve()
            skill = output / NAMES[0]
            skill.write_bytes(b'previous release')
            (output / NAMES[1]).mkdir()
            with self.assertRaises((ValueError, OSError)):
                builder.build(output)
            self.assertEqual(skill.read_bytes(), b'previous release')
            self.assertEqual(sorted(p.name for p in output.iterdir()), sorted(NAMES))

    def test_destination_symlink_is_rejected_without_following_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'output'
            output.mkdir()
            target = Path(tmp) / 'foreign'
            target.write_bytes(b'foreign data')
            (output / NAMES[1]).symlink_to(target)
            with self.assertRaises((ValueError, OSError)):
                builder.build(output)
            self.assertEqual(target.read_bytes(), b'foreign data')
            self.assertTrue((output / NAMES[1]).is_symlink())
            self.assertFalse((output / NAMES[0]).exists())

    def test_output_parent_alias_is_canonicalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'real').mkdir()
            (root / 'link').symlink_to(root / 'real', target_is_directory=True)
            builder.build(root / 'link' / 'output')
            self.assertEqual(sorted(p.name for p in (root / 'real' / 'output').iterdir()), sorted(NAMES))

    def test_output_directory_leaf_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'real').mkdir()
            (root / 'link').symlink_to(root / 'real', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                builder.build(root / 'link')
            self.assertEqual(list((root / 'real').iterdir()), [])

    def test_staged_archive_write_failure_preserves_existing_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve()
            previous = self.previous_release(output)
            original = zipfile.ZipFile.writestr
            writes = 0

            def fail_during_second_archive(archive, *args, **kwargs):
                nonlocal writes
                writes += 1
                if writes == len(builder.FILES) + 3:
                    raise OSError('injected staged write failure')
                return original(archive, *args, **kwargs)

            with patch.object(zipfile.ZipFile, 'writestr', fail_during_second_archive):
                with self.assertRaisesRegex(OSError, 'injected staged write failure'):
                    builder.build(output)
            self.assertEqual(self.snapshot(output), previous)
            self.assertEqual(sorted(p.name for p in output.iterdir()), sorted(NAMES))

    def test_second_promotion_failure_restores_previous_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve()
            previous = self.previous_release(output)
            original = os.replace
            failed = False

            def fail_second_promotion(source, destination):
                nonlocal failed
                if Path(destination) == output / NAMES[1] and not failed:
                    failed = True
                    raise OSError('injected promotion failure')
                return original(source, destination)

            with patch.object(os, 'replace', fail_second_promotion):
                with self.assertRaisesRegex(OSError, 'injected promotion failure'):
                    builder.build(output)
            self.assertTrue(failed)
            self.assertEqual(self.snapshot(output), previous)
            self.assertEqual(sorted(p.name for p in output.iterdir()), sorted(NAMES))

    def test_rollback_failure_retains_recoverable_previous_archives(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve()
            previous = self.previous_release(output)
            original = os.replace

            def fail_promotion_and_restore(source, destination):
                if Path(destination) == output / NAMES[1] or str(source).endswith('.previous'):
                    raise OSError('injected persistent filesystem failure')
                return original(source, destination)

            with patch.object(os, 'replace', fail_promotion_and_restore):
                with self.assertRaisesRegex(OSError, 'recovery files retained at'):
                    builder.build(output)
            recovery, = output.glob('.optimax-release-*')
            self.assertEqual({name: (recovery / (name + '.previous')).read_bytes() for name in NAMES}, previous)
            self.assertEqual((output / NAMES[1]).read_bytes(), previous[NAMES[1]])

    def test_failed_initial_promotion_leaves_no_partial_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve()
            original = os.replace

            def fail_second_promotion(source, destination):
                if Path(destination) == output / NAMES[1]:
                    raise OSError('injected promotion failure')
                return original(source, destination)

            with patch.object(os, 'replace', fail_second_promotion):
                with self.assertRaisesRegex(OSError, 'injected promotion failure'):
                    builder.build(output)
            self.assertEqual(list(output.iterdir()), [])

    def test_invalid_input_preserves_previous_pair_and_foreign_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve()
            previous = self.previous_release(output)
            foreign = output / 'notes.txt'
            foreign.write_bytes(b'keep')
            with patch.object(builder, 'FILES', (*builder.FILES, 'missing-file')):
                with self.assertRaisesRegex(ValueError, 'missing release file'):
                    builder.build(output)
            self.assertEqual(self.snapshot(output), previous)
            self.assertEqual(foreign.read_bytes(), b'keep')

    def test_repeat_build_is_deterministic_and_preserves_foreign_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve()
            foreign = output / 'notes.txt'
            foreign.write_bytes(b'keep')
            builder.build(output)
            previous = self.snapshot(output)
            builder.build(output)
            self.assertEqual(self.snapshot(output), previous)
            self.assertEqual(foreign.read_bytes(), b'keep')
            self.assertEqual(sorted(p.name for p in output.iterdir()), sorted((*NAMES, 'notes.txt')))


if __name__ == '__main__':
    unittest.main()
