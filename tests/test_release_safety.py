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

    def test_oversized_runtime_preserves_previous_pair_and_foreign_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve()
            previous = self.previous_release(output)
            foreign = output / 'foreign'
            foreign.write_bytes(b'keep')
            runtime = output / 'runtime'
            runtime.mkdir()
            for name in builder.FILES:
                target = runtime / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((builder.RUNTIME / name).read_bytes())
            (runtime / 'scripts/ladder.py').write_bytes(b'x' * (1024 * 1024 + 1))
            with patch.object(builder, 'RUNTIME', runtime):
                with self.assertRaisesRegex(ValueError, 'byte limit'):
                    builder.build(output)
            self.assertEqual(self.snapshot(output), previous)
            self.assertEqual(foreign.read_bytes(), b'keep')
            self.assertFalse(list(output.glob('.optimax-release-*')))

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

    def test_corrupt_staged_plugin_is_rejected_before_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve()
            previous = self.previous_release(output)
            foreign = output / 'foreign'
            foreign.write_bytes(b'keep')
            original_close = zipfile.ZipFile.close
            injected = False

            def corrupt_after_close(archive):
                nonlocal injected
                path = Path(archive.filename) if archive.filename else None
                should_corrupt = archive.mode == 'w' and path is not None and path.name == NAMES[1] and archive.fp is not None
                original_close(archive)
                if should_corrupt:
                    with path.open('r+b') as staged:
                        staged.write(b'X')
                    with zipfile.ZipFile(path) as probe:
                        with self.assertRaises(zipfile.BadZipFile):
                            probe.read(probe.infolist()[0])
                    injected = True

            error = None
            with patch.object(zipfile.ZipFile, 'close', corrupt_after_close):
                try:
                    builder.build(output)
                except (ValueError, OSError, zipfile.BadZipFile) as exc:
                    error = exc
            self.assertTrue(injected, 'fault must be injected after the plugin write closes')
            self.assertEqual(self.snapshot(output), previous)
            self.assertEqual(foreign.read_bytes(), b'keep')
            self.assertFalse(list(output.glob('.optimax-release-*')))
            self.assertIsNotNone(error, 'corrupt staged plugin must be rejected')

    def test_invalid_staged_plugin_contents_are_rejected_before_promotion(self):
        for fault in ('wrong_payload', 'missing', 'duplicate', 'extra', 'nonregular'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp).resolve()
                previous = self.previous_release(output)
                foreign = output / 'foreign'
                foreign.write_bytes(b'keep')
                original_close = zipfile.ZipFile.close
                injected = False

                def alter_after_close(archive):
                    nonlocal injected
                    path = Path(archive.filename) if archive.filename else None
                    should_alter = archive.mode == 'w' and path is not None and path.name == NAMES[1] and archive.fp is not None
                    original_close(archive)
                    if not should_alter:
                        return
                    with zipfile.ZipFile(path) as source:
                        entries = [(info, source.read(info)) for info in source.infolist()]
                    replacement = path.with_suffix('.replacement')
                    with zipfile.ZipFile(replacement, 'w') as target:
                        for index, (info, data) in enumerate(entries):
                            if index == 0 and fault == 'missing':
                                continue
                            if index == 0 and fault == 'wrong_payload':
                                data = bytes([data[0] ^ 1]) + data[1:]
                            if index == 0 and fault == 'nonregular':
                                info.external_attr = 0o120777 << 16
                            target.writestr(info, data)
                        if fault == 'duplicate':
                            target.writestr(entries[0][0], entries[0][1])
                        if fault == 'extra':
                            target.writestr('unexpected.txt', b'extra')
                    replacement.replace(path)
                    with zipfile.ZipFile(path) as probe:
                        self.assertIsNone(probe.testzip(), 'fault must have valid CRCs')
                    injected = True

                error = None
                with patch.object(zipfile.ZipFile, 'close', alter_after_close):
                    try:
                        builder.build(output)
                    except (ValueError, OSError, zipfile.BadZipFile) as exc:
                        error = exc
                self.assertTrue(injected, 'fault must be injected after plugin write closes')
                self.assertTrue(self.snapshot(output) == previous, 'previous pair changed')
                self.assertEqual(foreign.read_bytes(), b'keep')
                self.assertFalse(list(output.glob('.optimax-release-*')))
                self.assertIsNotNone(error, f'{fault} staged plugin must be rejected')

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

    def test_interruption_after_promotion_restores_existing_or_absent_pair(self):
        for existing in (False, True):
            for interrupted_index in (0, 1):
                with self.subTest(existing=existing, interrupted_index=interrupted_index):
                    with tempfile.TemporaryDirectory() as tmp:
                        output = Path(tmp).resolve()
                        previous = self.previous_release(output) if existing else {}
                        original = os.replace

                        def interrupt_after_replace(source, destination):
                            result = original(source, destination)
                            if (Path(destination) == output / NAMES[interrupted_index]
                                    and Path(source).name == NAMES[interrupted_index]):
                                raise KeyboardInterrupt('injected after promotion')
                            return result

                        with patch.object(os, 'replace', interrupt_after_replace):
                            with self.assertRaisesRegex(KeyboardInterrupt, 'injected after promotion'):
                                builder.build(output)
                        if existing:
                            self.assertTrue(self.snapshot(output) == previous, 'previous archive bytes not restored')
                        else:
                            self.assertEqual(list(output.iterdir()), [])
                        self.assertEqual(sorted(p.name for p in output.iterdir()), sorted(previous))

    def test_interruption_before_promotion_preserves_existing_or_absent_pair(self):
        for existing in (False, True):
            with self.subTest(existing=existing), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp).resolve()
                previous = self.previous_release(output) if existing else {}
                original = os.replace

                def interrupt_before_replace(source, destination):
                    if Path(destination) == output / NAMES[0]:
                        raise KeyboardInterrupt('injected before promotion')
                    return original(source, destination)

                with patch.object(os, 'replace', interrupt_before_replace):
                    with self.assertRaisesRegex(KeyboardInterrupt, 'injected before promotion'):
                        builder.build(output)
                if existing:
                    self.assertEqual(self.snapshot(output), previous)
                self.assertEqual(sorted(p.name for p in output.iterdir()), sorted(previous))

    def test_foreign_replacement_is_preserved_and_recovery_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve()
            previous = self.previous_release(output)
            original = os.replace

            def replace_with_foreign_then_interrupt(source, destination):
                if Path(destination) == output / NAMES[0] and Path(source).name == NAMES[0]:
                    original(source, destination)
                    foreign = output / 'foreign'
                    foreign.write_bytes(b'foreign replacement')
                    original(foreign, destination)
                    raise KeyboardInterrupt('injected promotion interruption')
                return original(source, destination)

            with patch.object(os, 'replace', replace_with_foreign_then_interrupt):
                with self.assertRaisesRegex(OSError, 'recovery files retained at') as caught:
                    builder.build(output)
            self.assertIsInstance(caught.exception.__context__, KeyboardInterrupt)
            self.assertEqual((output / NAMES[0]).read_bytes(), b'foreign replacement')
            recovery, = output.glob('.optimax-release-*')
            self.assertEqual((recovery / (NAMES[0] + '.previous')).read_bytes(), previous[NAMES[0]])

    def test_interruption_during_rollback_retains_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve()
            previous = self.previous_release(output)
            original = os.replace

            def interrupt_promotion_and_rollback(source, destination):
                if Path(destination) == output / NAMES[1] and Path(source).name == NAMES[1]:
                    raise OSError('injected promotion failure')
                if str(source).endswith('.previous'):
                    raise KeyboardInterrupt('injected rollback interruption')
                return original(source, destination)

            with patch.object(os, 'replace', interrupt_promotion_and_rollback):
                with self.assertRaisesRegex(OSError, 'recovery files retained at') as caught:
                    builder.build(output)
            self.assertIsInstance(caught.exception.__context__, OSError)
            recovery, = output.glob('.optimax-release-*')
            self.assertEqual((recovery / (NAMES[0] + '.previous')).read_bytes(), previous[NAMES[0]])

    def test_interrupted_promotion_restores_mixed_prior_state(self):
        for existing_index in (0, 1):
            with self.subTest(existing_index=existing_index), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp).resolve()
                destination = output / NAMES[existing_index]
                destination.write_bytes(b'previous archive')
                original = os.replace

                def interrupt_second(source, target):
                    result = original(source, target)
                    if Path(target) == output / NAMES[1] and Path(source).name == NAMES[1]:
                        raise KeyboardInterrupt('interrupted mixed promotion')
                    return result

                with patch.object(os, 'replace', interrupt_second):
                    with self.assertRaisesRegex(KeyboardInterrupt, 'interrupted mixed promotion'):
                        builder.build(output)
                self.assertEqual(destination.read_bytes(), b'previous archive')
                self.assertEqual(sorted(p.name for p in output.iterdir()), [NAMES[existing_index]])

    def test_interruption_after_rollback_rename_retains_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve()
            previous = self.previous_release(output)
            original = os.replace

            def interrupt_after_restore(source, destination):
                if Path(destination) == output / NAMES[1] and Path(source).name == NAMES[1]:
                    raise OSError('injected promotion failure')
                result = original(source, destination)
                if str(source).endswith('.previous'):
                    raise KeyboardInterrupt('interrupted after restoration')
                return result

            with patch.object(os, 'replace', interrupt_after_restore):
                with self.assertRaisesRegex(OSError, 'recovery files retained at'):
                    builder.build(output)
            self.assertEqual((output / NAMES[0]).read_bytes(), previous[NAMES[0]])
            recovery, = output.glob('.optimax-release-*')
            self.assertEqual((recovery / (NAMES[1] + '.previous')).read_bytes(), previous[NAMES[1]])

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
