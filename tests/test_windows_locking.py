"""Portable regressions for Windows lock selection, errors, and cleanup.

The real-lock adapter qualifies the controller's file selection and exclusion
on POSIX. Native msvcrt behavior and Windows filesystem semantics need Windows.
"""
import errno
import hashlib
import multiprocessing
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import sys
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/optimax/scripts"))
import performance

REAL_FCNTL = performance.fcntl


class FlockAdapter:
    """Use real process locks while exposing msvcrt's contention errno."""
    LK_NBLCK = 1
    LK_UNLCK = 2

    def __init__(self, events=None):
        self.events = events
        self.attempted = False
        self.blocked = False
        self.operations = []

    def locking(self, descriptor, mode, count):
        self.operations.append(mode)
        if mode == self.LK_UNLCK:
            REAL_FCNTL.flock(descriptor, REAL_FCNTL.LOCK_UN)
            return
        if self.events is not None and not self.attempted:
            self.events.put("attempting")
            self.attempted = True
        try:
            REAL_FCNTL.flock(descriptor, REAL_FCNTL.LOCK_EX | REAL_FCNTL.LOCK_NB)
        except BlockingIOError as error:
            if self.events is not None and not self.blocked:
                self.events.put("blocked")
                self.blocked = True
            raise OSError(errno.EACCES, "lock is held by another process") from error


def hold_windows_lock(root, home, temporary, events, release):
    """Spawned worker: actual opens and locks, with independently cached TMP."""
    os.environ.update(HOME=home, USERPROFILE=home,
                      TMPDIR=temporary, TEMP=temporary, TMP=temporary)
    tempfile.tempdir = None
    adapter = FlockAdapter(events)
    with patch.object(performance, "fcntl", None), \
            patch.object(performance, "msvcrt", adapter, create=True), \
            patch.object(performance, "time", time, create=True):
        with performance.Engine(root, "worker-user")._locked():
            events.put("acquired")
            if not release.wait(10):
                raise TimeoutError("test did not release the held lock")
        events.put("released")


class WindowsLockingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.root = self.base / "project"
        self.home = self.base / "profile"
        self.temp_a = self.base / "temp-a"
        self.temp_b = self.base / "temp-b"
        for directory in (self.root, self.home, self.temp_a, self.temp_b):
            directory.mkdir()
        environment = dict(HOME=str(self.home), USERPROFILE=str(self.home),
                           TMPDIR=str(self.temp_a), TEMP=str(self.temp_a),
                           TMP=str(self.temp_a))
        environment_patch = patch.dict(os.environ, environment)
        environment_patch.start()
        self.addCleanup(environment_patch.stop)
        temp_patch = patch.object(tempfile, "tempdir", None)
        temp_patch.start()
        self.addCleanup(temp_patch.stop)
        self.engine = performance.Engine(self.root, "actual-user")

    def windows(self, adapter, sleeper=None):
        """Patch platform APIs only; file opening and safe paths stay real."""
        from contextlib import ExitStack
        stack = ExitStack()
        stack.enter_context(patch.object(performance, "fcntl", None))
        stack.enter_context(patch.object(performance, "msvcrt", adapter, create=True))
        stack.enter_context(patch.object(
            performance, "time", SimpleNamespace(sleep=sleeper or Mock()), create=True))
        self.addCleanup(stack.close)
        return stack

    def test_windows_root_guard_spans_validation_and_ledger_creation(self):
        import ctypes
        opened = []
        closed = []
        kernel = SimpleNamespace(CreateFileW=Mock(), GetFileInformationByHandleEx=Mock(),
                                 CloseHandle=Mock(side_effect=closed.append))
        def create(path, *args):
            opened.append(path)
            return len(opened) + 100
        def attributes(handle, kind, info, size):
            info._obj.FileAttributes = 0x10
            return 1
        kernel.CreateFileW.side_effect = create
        kernel.GetFileInformationByHandleEx.side_effect = attributes
        original_check = self.engine._safe_paths
        def check():
            self.assertIn(str(self.engine.root), opened, 'root must be pinned before path validation')
            self.assertNotIn(101, closed, 'root guard released during transaction')
            original_check()
        adapter = SimpleNamespace(LK_NBLCK=1, LK_UNLCK=2, locking=Mock())
        with self.windows(adapter), patch.object(sys, 'platform', 'win32'), \
                patch.object(ctypes, 'WinDLL', return_value=kernel, create=True), \
                patch.object(self.engine, '_safe_paths', side_effect=check):
            self.engine.set_enabled('session', True)
        self.assertEqual(opened[0], str(self.engine.root))
        self.assertEqual(closed[-1], 101, 'root handle must outlive ledger handles')
        self.assertEqual(len(closed), len(opened))
        self.assertTrue(self.engine.path.exists())
        for call in kernel.CreateFileW.call_args_list:
            self.assertEqual(call.args[2] & 0x4, 0)
            self.assertEqual(call.args[5] & 0x02200000, 0x02200000)

    def test_windows_child_guard_is_retained_from_read_through_commit(self):
        import ctypes
        self.engine.set_enabled('session', True)
        closed = []
        kernel = SimpleNamespace(CreateFileW=Mock(side_effect=[101, 102]),
                                 GetFileInformationByHandleEx=Mock(),
                                 CloseHandle=Mock(side_effect=closed.append))
        def attributes(handle, kind, info, size):
            info._obj.FileAttributes = 0x10
            return 1
        kernel.GetFileInformationByHandleEx.side_effect = attributes
        load = self.engine._load
        loaded = False
        def observe_load(access):
            nonlocal loaded
            rows = load(access)
            loaded = True
            self.assertEqual(kernel.CreateFileW.call_count, 2)
            self.assertEqual(closed, [], 'root and child must both remain pinned after ledger read')
            return rows
        adapter = SimpleNamespace(LK_NBLCK=1, LK_UNLCK=2, locking=Mock())
        with self.windows(adapter), patch.object(sys, 'platform', 'win32'), \
                patch.object(ctypes, 'WinDLL', return_value=kernel, create=True), \
                patch.object(self.engine, '_load', side_effect=observe_load):
            self.engine.set_enabled('session', False)
        self.assertTrue(loaded)
        self.assertEqual([call.args[0] for call in kernel.CreateFileW.call_args_list],
                         [str(self.engine.root), str(self.engine.directory)],
                         'commit must reuse the child guard acquired before load')
        self.assertEqual(closed, [102, 101])
        self.assertFalse(self.engine.status('session')['enabled'])

    def test_windows_root_guard_rejects_reparse_before_creation_and_releases_lock(self):
        import ctypes
        kernel = SimpleNamespace(CreateFileW=Mock(return_value=123),
                                 GetFileInformationByHandleEx=Mock(), CloseHandle=Mock())
        def attributes(handle, kind, info, size):
            info._obj.FileAttributes = 0x410
            return 1
        kernel.GetFileInformationByHandleEx.side_effect = attributes
        adapter = SimpleNamespace(LK_NBLCK=1, LK_UNLCK=2, locking=Mock())
        with self.windows(adapter), patch.object(sys, 'platform', 'win32'), \
                patch.object(ctypes, 'WinDLL', return_value=kernel, create=True):
            with self.assertRaisesRegex(ValueError, 'reparse'):
                self.engine.set_enabled('session', True)
        self.assertFalse(self.engine.directory.exists())
        kernel.CreateFileW.assert_called_once()
        self.assertEqual(kernel.CreateFileW.call_args.args[0], str(self.engine.root))
        kernel.CloseHandle.assert_called_once_with(123)
        self.assertEqual([call.args[1] for call in adapter.locking.call_args_list], [1, 2])

    def test_windows_root_guard_closes_on_interruption_and_releases_lock(self):
        import ctypes
        kernel = SimpleNamespace(CreateFileW=Mock(return_value=123),
                                 GetFileInformationByHandleEx=Mock(), CloseHandle=Mock())
        def attributes(handle, kind, info, size):
            info._obj.FileAttributes = 0x10
            return 1
        kernel.GetFileInformationByHandleEx.side_effect = attributes
        adapter = SimpleNamespace(LK_NBLCK=1, LK_UNLCK=2, locking=Mock())
        with self.windows(adapter), patch.object(sys, 'platform', 'win32'), \
                patch.object(ctypes, 'WinDLL', return_value=kernel, create=True), \
                patch.object(self.engine, '_safe_paths', side_effect=KeyboardInterrupt()):
            with self.assertRaises(KeyboardInterrupt):
                self.engine.set_enabled('session', True)
        self.assertFalse(self.engine.directory.exists())
        kernel.CloseHandle.assert_called_once_with(123)
        self.assertEqual([call.args[1] for call in adapter.locking.call_args_list], [1, 2])

    def test_windows_directory_guard_denies_rename_and_closes_after_interruption(self):
        import ctypes
        self.engine.directory.mkdir()
        kernel = SimpleNamespace(CreateFileW=Mock(return_value=123),
                                 GetFileInformationByHandleEx=Mock(return_value=1),
                                 CloseHandle=Mock(return_value=1))
        def attributes(handle, kind, info, size):
            info._obj.FileAttributes = 0x10
            return 1
        kernel.GetFileInformationByHandleEx.side_effect = attributes
        with patch.object(sys, 'platform', 'win32'), \
                patch.object(ctypes, 'WinDLL', return_value=kernel, create=True):
            self.engine.set_enabled('session', True)
            original = self.engine.path.read_bytes()
            with patch('performance.os.replace', side_effect=KeyboardInterrupt()):
                with self.assertRaises(KeyboardInterrupt):
                    self.engine.set_enabled('session', False)
            self.assertEqual(self.engine.path.read_bytes(), original)
            self.assertEqual(list(self.engine.directory.iterdir()), [self.engine.path])
        kernel.CreateFileW.assert_called()
        for call in kernel.CreateFileW.call_args_list:
            self.assertEqual(call.args[2] & 0x4, 0, 'guard must deny FILE_SHARE_DELETE')
            self.assertEqual(call.args[4], 3, 'guard opens existing directory')
            self.assertEqual(call.args[5] & 0x02200000, 0x02200000)
        self.assertEqual(kernel.CloseHandle.call_count, kernel.CreateFileW.call_count)

    def test_windows_directory_guard_rejects_reparse_and_non_directory_before_write(self):
        import ctypes
        for value in (0x410, 0x80):
            with self.subTest(attributes=value):
                self.engine.directory.mkdir(exist_ok=True)
                kernel = SimpleNamespace(CreateFileW=Mock(side_effect=[101, 123]),
                                         GetFileInformationByHandleEx=Mock(),
                                         CloseHandle=Mock(return_value=1))
                def attributes(handle, kind, info, size):
                    info._obj.FileAttributes = 0x10 if handle == 101 else value
                    return 1
                kernel.GetFileInformationByHandleEx.side_effect = attributes
                adapter = SimpleNamespace(LK_NBLCK=1, LK_UNLCK=2, locking=Mock())
                with self.windows(adapter), patch.object(sys, 'platform', 'win32'), \
                        patch.object(ctypes, 'WinDLL', return_value=kernel, create=True):
                    with self.assertRaisesRegex(ValueError, 'reparse'):
                        self.engine.set_enabled('session', True)
                self.assertEqual(list(self.engine.directory.iterdir()), [])
                self.assertEqual([call.args[0] for call in kernel.CreateFileW.call_args_list],
                                 [str(self.engine.root), str(self.engine.directory)])
                self.assertEqual([call.args[0] for call in kernel.CloseHandle.call_args_list],
                                 [123, 101], 'child and root guards must both close')
                self.assertEqual([call.args[1] for call in adapter.locking.call_args_list], [1, 2])

    def test_windows_directory_guard_api_failures_do_not_write_and_close_valid_handles(self):
        import ctypes
        self.engine.directory.mkdir()
        invalid = ctypes.c_void_p(-1).value
        for handle, query_result in ((invalid, 1), (123, 0)):
            with self.subTest(handle=handle, query_result=query_result):
                kernel = SimpleNamespace(CreateFileW=Mock(side_effect=[101, handle]),
                                         GetFileInformationByHandleEx=Mock(),
                                         CloseHandle=Mock(return_value=1))
                def attributes(current, kind, info, size):
                    info._obj.FileAttributes = 0x10
                    return 1 if current == 101 else query_result
                kernel.GetFileInformationByHandleEx.side_effect = attributes
                adapter = SimpleNamespace(LK_NBLCK=1, LK_UNLCK=2, locking=Mock())
                with self.windows(adapter), patch.object(sys, 'platform', 'win32'), \
                        patch.object(ctypes, 'WinDLL', return_value=kernel, create=True):
                    with self.assertRaises(OSError):
                        self.engine.set_enabled('session', True)
                self.assertEqual(list(self.engine.directory.iterdir()), [])
                self.assertEqual([call.args[0] for call in kernel.CreateFileW.call_args_list],
                                 [str(self.engine.root), str(self.engine.directory)])
                expected_closed = [101] if handle == invalid else [handle, 101]
                self.assertEqual([call.args[0] for call in kernel.CloseHandle.call_args_list],
                                 expected_closed)
                expected_queried = [101] if handle == invalid else [101, handle]
                self.assertEqual([call.args[0] for call in kernel.GetFileInformationByHandleEx.call_args_list],
                                 expected_queried)
                self.assertEqual([call.args[1] for call in adapter.locking.call_args_list], [1, 2])

    def test_permanent_lock_errors_propagate_without_retry(self):
        for number in (errno.EINVAL, errno.EBADF):
            with self.subTest(errno=number):
                error = OSError(number, "permanent lock error")
                locking = Mock(side_effect=error)
                sleeper = Mock(side_effect=AssertionError(
                    "permanent lock errors must propagate instead of retrying"))
                adapter = SimpleNamespace(LK_NBLCK=1, LK_UNLCK=2, locking=locking)
                with self.windows(adapter, sleeper):
                    with self.assertRaises(OSError) as raised:
                        with self.engine._locked():
                            self.fail("body must not run after a lock error")
                self.assertIs(raised.exception, error)
                self.assertEqual(locking.call_count, 1)
                sleeper.assert_not_called()

    def test_access_denied_contention_retries_then_releases(self):
        locking = Mock(side_effect=[
            OSError(errno.EACCES, "busy"), OSError(errno.EACCES, "busy"), None, None])
        sleeper = Mock()
        adapter = SimpleNamespace(LK_NBLCK=1, LK_UNLCK=2, locking=locking)
        with self.windows(adapter, sleeper):
            with self.engine._locked():
                self.assertFalse(self.engine.path.exists())
        self.assertEqual([call.args[1] for call in locking.call_args_list], [1, 1, 1, 2])
        self.assertEqual(sleeper.call_count, 2)

    def test_lock_is_retained_in_profile_cache_outside_project_and_temp(self):
        adapter = SimpleNamespace(LK_NBLCK=1, LK_UNLCK=2, locking=Mock())
        digest = hashlib.sha256(str(self.engine.root).lower().encode("utf-8")).hexdigest()[:32]
        expected = self.home / ".optimax" / "locks" / (digest + ".lock")
        with self.windows(adapter):
            with self.engine._locked():
                self.assertTrue(expected.is_file(), "lock must use the stable profile namespace")
        self.assertTrue(expected.is_file(), "unlinking permits concurrent lock namespaces")
        self.assertEqual(list(self.root.iterdir()), [])
        self.assertEqual(list(self.temp_a.iterdir()), [])

    def test_unavailable_profile_cache_fails_without_ledger_or_temp_fallback(self):
        (self.home / ".optimax").write_text("not a directory", encoding="utf-8")
        adapter = SimpleNamespace(LK_NBLCK=1, LK_UNLCK=2, locking=Mock())
        with self.windows(adapter):
            with self.assertRaises(OSError):
                self.engine.set_enabled("session", True)
        self.assertEqual(list(self.root.iterdir()), [])
        self.assertEqual(list(self.temp_a.iterdir()), [])
        adapter.locking.assert_not_called()

    @unittest.skipUnless(REAL_FCNTL is not None, "portable real-lock adapter requires POSIX flock")
    def test_body_errors_and_symlink_rejection_release_the_lock(self):
        adapter = FlockAdapter()
        with self.windows(adapter, time.sleep):
            with self.assertRaisesRegex(RuntimeError, "body failed"):
                with self.engine._locked():
                    raise RuntimeError("body failed")
            outside = self.base / "outside"
            outside.mkdir()
            self.engine.directory.symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlinks"):
                with self.engine._locked():
                    self.fail("unsafe ledger body must not run")
            self.engine.directory.unlink()
            with self.engine._locked():
                pass
        self.assertEqual(adapter.operations, [1, 2, 1, 2, 1, 2])
        self.assertEqual(list(outside.iterdir()), [])

    @unittest.skipUnless(REAL_FCNTL is not None, "portable real-lock adapter requires POSIX flock")
    def test_different_temp_environments_share_real_lock_for_canonical_project(self):
        alias = self.base / "project-alias"
        alias.symlink_to(self.root, target_is_directory=True)
        context = multiprocessing.get_context("spawn")
        first_events, second_events = context.Queue(), context.Queue()
        first_release, second_release = context.Event(), context.Event()
        processes = [
            context.Process(target=hold_windows_lock, args=(
                str(root), str(self.home), str(temporary), events, release))
            for root, temporary, events, release in (
                (self.root, self.temp_a, first_events, first_release),
                (alias, self.temp_b, second_events, second_release))
        ]
        try:
            processes[0].start()
            self.assertEqual(first_events.get(timeout=5), "attempting")
            self.assertEqual(first_events.get(timeout=5), "acquired")
            processes[1].start()
            self.assertEqual(second_events.get(timeout=5), "attempting")
            self.assertEqual(second_events.get(timeout=5), "blocked",
                             "different TMP environments must not split the project lock")
            first_release.set()
            self.assertEqual(first_events.get(timeout=5), "released")
            self.assertEqual(second_events.get(timeout=5), "acquired")
            second_release.set()
            self.assertEqual(second_events.get(timeout=5), "released")
        finally:
            first_release.set()
            second_release.set()
            for process in processes:
                if process.pid is not None:
                    process.join(timeout=5)
                    if process.is_alive():
                        process.terminate()
                        process.join(timeout=5)
            for events in (first_events, second_events):
                events.close()
                events.join_thread()
        self.assertEqual([process.exitcode for process in processes], [0, 0])

    @unittest.skipUnless(REAL_FCNTL is not None, "POSIX-specific baseline")
    def test_posix_directory_lock_and_exception_cleanup_remain_supported(self):
        descriptor = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            with patch.object(self.engine, "_locked_windows",
                              side_effect=AssertionError("POSIX must keep its directory lock")):
                with self.assertRaisesRegex(RuntimeError, "body failed"):
                    with self.engine._locked():
                        with self.assertRaises(BlockingIOError):
                            REAL_FCNTL.flock(descriptor, REAL_FCNTL.LOCK_EX | REAL_FCNTL.LOCK_NB)
                        raise RuntimeError("body failed")
            REAL_FCNTL.flock(descriptor, REAL_FCNTL.LOCK_EX | REAL_FCNTL.LOCK_NB)
        finally:
            REAL_FCNTL.flock(descriptor, REAL_FCNTL.LOCK_UN)
            os.close(descriptor)


if __name__ == "__main__":
    unittest.main()
