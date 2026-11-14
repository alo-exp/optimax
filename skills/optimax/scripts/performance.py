"""Stdlib controller for one canonical project and explicit user.

All durable state is one versioned CSV. flock on the project directory (POSIX)
or msvcrt locking on a per-project file in the user profile cache (Windows)
serializes cooperating controllers; fsync and atomic rename publish updates
without lock or state sidecars in the project. Requires a local filesystem;
Windows controllers must share the same resolved profile with a writable cache.
Network filesystems are unsupported. The trusted host resolves exact model IDs, discovers supported
rungs, dispatches natively, and independently reviews actual execution receipts.
This engine never launches agents or changes native/global model settings.

adopt_policy() or the first successful prepare appends ordered v1-to-v2-to-v3-to-v4
policy events. Historical rows retain their original ordinal semantics. V2
retires old Executor tracks; v3 preserves compatible Executor epochs/windows
and retires old Advisor tracks. V4 preserves Executor and Codex Advisor tracks
and retires Claude Advisor tracks. New Advisors carry per-consultation advice
levels, not complexity tiers. Assessments apply each prepared run's context floor.
Status never adopts. Explicit on returns unapplied orchestrator suggestions.
"""
import argparse
from contextlib import contextmanager, ExitStack, nullcontext
import csv
import ctypes
from datetime import datetime, timezone
import errno
try:
    import fcntl
except ImportError:  # Windows: lock a per-project file in the profile cache
    fcntl = None
    import msvcrt
    import time
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import uuid

# Match a ceiling supported by both older C-long and newer Py_ssize_t codecs.
_CSV_FIELD_LIMIT = min(sys.maxsize, (1 << (ctypes.sizeof(ctypes.c_long) * 8 - 1)) - 1)
_CSV_READER_CODE = """
import csv
import io
import json
import sys
csv.field_size_limit(int(sys.argv[1]))
try:
    stream = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", newline="")
    reader = csv.DictReader(stream, strict=True)
    header = reader.fieldnames or []
    rows = list(reader)
except (csv.Error, UnicodeError):
    print("invalid ledger CSV", file=sys.stderr)
    raise SystemExit(1)
print(json.dumps([header, rows], ensure_ascii=True, separators=(",", ":")))
"""

try:
    from .ladder import (_FLOORS, _LADDERS, _TRACK_FIELDS, _validate_fields, ADVICE_FLOORS, LEGACY_POLICY_VERSION,
                         SECOND_POLICY_VERSION, THIRD_POLICY_VERSION, POLICY_VERSION, policy, policy_lineage, recommend)
    from .session_policy import advisor_context, execution_contract, orchestrator_recommendation
    from .instruction_audit import audit_instructions
except ImportError:
    from ladder import (_FLOORS, _LADDERS, _TRACK_FIELDS, _validate_fields, ADVICE_FLOORS, LEGACY_POLICY_VERSION,
                        SECOND_POLICY_VERSION, THIRD_POLICY_VERSION, POLICY_VERSION, policy, policy_lineage, recommend)
    from session_policy import advisor_context, execution_contract, orchestrator_recommendation
    from instruction_audit import audit_instructions

SCHEMA_VERSION = "2"
PROJECTIONS = ("platform", "role", "tier", "run_id", "epoch")
FIELDS = ("schema_version", "sequence", "timestamp", "event_type", "user_id", *PROJECTIONS, "data")
LEGACY_FIELDS = tuple(field for field in FIELDS if field != "tier")
EVENT_TYPES = {"metadata", "session", "transition", "launch", "assessment", "legacy_import", "policy_adoption", "advisor_context", "relocation"}


def _string(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 4096:
        raise ValueError(label + " must be a nonempty string of at most 4096 characters")

def _validate_mode(platform, mode):
    if mode not in ("direct", "codex-ultra", "claude-ultracode"):
        raise ValueError("invalid mode")
    if mode != "direct" and not mode.startswith(platform + "-"):
        raise ValueError("mode must match platform")


def _validate_capabilities(validation, models):
    selection = recommend(validation)
    if not isinstance(models, dict):
        raise ValueError("models must map logical family to resolved exact model ID")
    track = validation["track"]
    ladders, _ = policy(validation.get("policy_version", POLICY_VERSION))
    ladder = ladders[(track["platform"], track["role"])]
    for step in validation["available_steps"]:
        family = ladder[step][0]
        if family not in models:
            raise ValueError("models must resolve every available family")
        _string(models[family], "exact model ID")
    return selection



def _validate_assessment_request(request):
    for field in ("run_id", "effective_model_id", "effective_effort", "execution_id"):
        _string(request[field], field)
    if type(request["score"]) is not int or not 0 <= request["score"] <= 5:
        raise ValueError("score must be an integer from 0 to 5")
    if type(request["verified"]) is not bool:
        raise ValueError("verified must be a boolean")


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)

def _read_ledger_csv(stream):
    try:
        reader = csv.DictReader(stream, strict=True)
        return tuple(reader.fieldnames or ()), list(reader)
    except csv.Error:
        # Discard the failed parse and reuse the guarded descriptor, never its path.
        stream.seek(0)
    with subprocess.Popen(
            [sys.executable, "-I", "-c", _CSV_READER_CODE, str(_CSV_FIELD_LIMIT)],
            stdin=stream, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            shell=False, close_fds=True) as process:
        try:
            output, _ = process.communicate()
        except BaseException:
            process.kill()
            process.wait()
            raise
        if process.returncode:
            raise ValueError("isolated ledger CSV reader failed")
    try:
        payload = json.loads(output.decode("utf-8"))
    except (UnicodeError, ValueError, AttributeError):
        raise ValueError("invalid isolated ledger CSV response") from None
    if (not isinstance(payload, list) or len(payload) != 2
            or not isinstance(payload[0], list)
            or any(not isinstance(field, str) for field in payload[0])
            or not isinstance(payload[1], list)
            or any(not isinstance(row, dict)
                   or any(not isinstance(field, str) or (value is not None and not isinstance(value, str))
                          for field, value in row.items())
                   for row in payload[1])):
        raise ValueError("invalid isolated ledger CSV response")
    return tuple(payload[0]), payload[1]

def _write_ledger_csv(stream, rows):
    # The parser counts decoded characters, excluding CSV quoting and encoding.
    field_limit = _CSV_FIELD_LIMIT
    for field in FIELDS:
        if len(field) > field_limit:
            raise ValueError(f"CSV header field {field} exceeds parser field limit {field_limit}")
    writer = csv.DictWriter(stream, fieldnames=FIELDS)
    writer.writeheader()
    for row in rows:
        serialized = dict(row, data=_json(row["data"]))
        for field in FIELDS:
            value = serialized[field]
            if len("" if value is None else str(value)) > field_limit:
                raise ValueError(f"CSV event field {field} exceeds parser field limit {field_limit}")
        writer.writerow(serialized)

def _legacy_payload(rows):
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("legacy rows must be a list of objects")
    pending, seen = [rows], set()
    while pending:
        value = pending.pop()
        if isinstance(value, (dict, list, tuple)) and id(value) not in seen:
            seen.add(id(value))
            if isinstance(value, dict):
                if any(not isinstance(key, str) for key in value):
                    raise ValueError("legacy JSON object keys must be strings")
                pending.extend(value.values())
            else:
                pending.extend(value)
    payload = _json(rows)
    return payload, hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validate_consultation(platform, consultation, advice_level):
    if not isinstance(consultation, dict):
        raise ValueError("invalid stored consultation")
    purpose, complexity, needed = (consultation[field] for field in ("purpose", "complexity", "needed"))
    expected = dict(advisor_context(platform, complexity, purpose, needed),
                    purpose=purpose, complexity=complexity, needed=needed)
    actual = {field: consultation[field] for field in expected}
    if (_json(actual) != _json(expected) or not expected["consult"]
            or ADVICE_FLOORS[advice_level] < expected["starting_step"]):
        raise ValueError("invalid stored consultation")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _key(track):
    return (track["platform"], track["role"], track["tier"])


def _projection(data):
    attribution = data.get("attribution", data)
    return {field: "" if attribution.get(field) is None else attribution[field]
            for field in PROJECTIONS}


class _Access:
    """Directory bindings owned by one locked transaction."""

    def __init__(self, root_fd, guards):
        self.root_fd = root_fd
        self.guards = guards
        self.directory_present = False
        self.ledger_present = False
        self.directory_fd = None
        self.directory_identity = None
        self.namespace_confirmed = False


class Engine:
    """Reserve settings and record independently reviewed execution receipts."""

    def __init__(self, root, user):
        if not isinstance(user, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", user):
            raise ValueError("user must be an explicit safe user ID (letters, digits, _, ., -)")
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("root must be an existing project directory")
        self.user = user
        self.directory = self.root / "model-perf"
        self.path = self.directory / (user + "-model-perf.csv")
        self._root_identity = self.root.stat()

    @contextmanager
    def _locked(self):
        if fcntl is None:
            with self._locked_windows():
                with self._transaction(None) as access:
                    yield access
            return
        descriptor = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            self._check_root_identity(descriptor)
            self._safe_paths()
            self._check_root_identity(descriptor)
            with self._transaction(descriptor) as access:
                yield access
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    @contextmanager
    def _locked_windows(self):
        # Directories cannot be opened or locked on Windows, and a sidecar in the
        # project would alter the ledger directory, so lock outside the project.
        digest = hashlib.sha256(str(self.root).lower().encode("utf-8")).hexdigest()[:32]
        # Keep one namespace across processes with different temp environments.
        # Retain lock files: unlinking can split active locks across file objects.
        lock_directory = Path.home() / ".optimax" / "locks"
        lock_directory.mkdir(parents=True, exist_ok=True)
        lock_path = lock_directory / (digest + ".lock")
        with open(lock_path, "a+b") as stream:
            while True:
                try:
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as error:
                    if error.errno != errno.EACCES:  # CRT lock contention
                        raise
                    time.sleep(0.05)
            try:
                with self._windows_directory_guard(self.root):
                    self._check_root_identity()
                    self._safe_paths()
                    yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)

    def _safe_paths(self):
        for path in (self.directory, self.path):
            if path.is_symlink():
                raise ValueError("ledger paths must not be symlinks")
        if self.directory.exists() and not self.directory.is_dir():
            raise ValueError("model-perf must be a directory")
        if self.path.exists() and not stat.S_ISREG(self.path.stat().st_mode):
            raise ValueError("ledger must be a regular file")

    def _check_root_identity(self, root_fd=None):
        if isinstance(root_fd, _Access):
            root_fd = root_fd.root_fd
        current = self.root.stat(follow_symlinks=False)
        if (not stat.S_ISDIR(current.st_mode)
                or not os.path.samestat(current, self._root_identity)
                or (root_fd is not None and not os.path.samestat(current, os.fstat(root_fd)))):
            raise ValueError("project root changed during transaction")

    @contextmanager
    def _transaction(self, root_fd):
        with ExitStack() as guards:
            access = _Access(root_fd, guards)
            self._check_root_identity(root_fd)
            if sys.platform != "win32" or self.directory.exists():
                try:
                    self._bind_directory(access)
                except FileNotFoundError:
                    self._check_root_identity(root_fd)
            yield access

    def _bind_directory(self, access):
        access.directory_fd = access.guards.enter_context(self._directory_guard(access.root_fd))
        access.directory_identity = (os.fstat(access.directory_fd) if access.directory_fd is not None
                                     else self.directory.stat(follow_symlinks=False))
        access.directory_present = True

    def _check_access(self, access):
        self._check_root_identity(access.root_fd)
        if access.directory_present:
            directory = self.directory.name if access.root_fd is not None else self.directory
            current = os.stat(directory, dir_fd=access.root_fd, follow_symlinks=False)
            if (not stat.S_ISDIR(current.st_mode)
                    or not os.path.samestat(current, access.directory_identity)):
                raise ValueError("ledger directory changed during transaction")

    @contextmanager
    def _directory_guard(self, root_fd=None):
        self._check_root_identity(root_fd)
        if sys.platform != "win32":
            directory = self.directory.name if root_fd is not None else self.directory
            descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                 dir_fd=root_fd)
            try:
                yield descriptor
            finally:
                os.close(descriptor)
            return
        with self._windows_directory_guard(self.directory):
            yield None

    @contextmanager
    def _windows_directory_guard(self, directory):
        # A no-delete-sharing handle pins the directory's name on Windows.
        if sys.platform != "win32":
            yield None
            return
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                       ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                                       wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.GetFileInformationByHandleEx.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel.GetFileInformationByHandleEx.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL

        class AttributeTagInfo(ctypes.Structure):
            _fields_ = [("FileAttributes", wintypes.DWORD), ("ReparseTag", wintypes.DWORD)]

        handle = kernel.CreateFileW(str(directory), 0x80, 0x3, None, 3, 0x02200000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise OSError("cannot guard ledger directory")
        try:
            info = AttributeTagInfo()
            if not kernel.GetFileInformationByHandleEx(handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
                raise OSError("cannot inspect ledger directory")
            if info.FileAttributes & 0x400 or not info.FileAttributes & 0x10:
                raise ValueError("ledger directory must be a directory without reparse points")
            yield None
        finally:
            kernel.CloseHandle(handle)

    def _check_directory_identity(self, descriptor, root_fd=None):
        self._check_root_identity(root_fd)
        directory = self.directory.name if root_fd is not None else self.directory
        current = os.stat(directory, dir_fd=root_fd, follow_symlinks=False)
        if not stat.S_ISDIR(current.st_mode) or not os.path.samestat(current, os.fstat(descriptor)):
            raise ValueError("ledger directory changed during mutation")

    def _load(self, root_fd=None, expected_root=None):
        if not isinstance(root_fd, _Access):
            with self._transaction(root_fd) as access:
                return self._load(access, expected_root)
        access = root_fd
        self._check_access(access)
        if not access.directory_present:
            return []
        with nullcontext(access.directory_fd) as directory_fd:
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
            try:
                if directory_fd is None:
                    descriptor = os.open(self.path, flags)
                else:
                    descriptor = os.open(self.path.name, flags, dir_fd=directory_fd)
            except FileNotFoundError:
                self._check_root_identity(root_fd)
                return []
            with os.fdopen(descriptor, "r", newline="", encoding="utf-8") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise ValueError("ledger must be a regular file")
                access.ledger_present = True
                header, rows = _read_ledger_csv(stream)
                if header not in (FIELDS, LEGACY_FIELDS):
                    raise ValueError("unsupported or corrupt ledger header")
                version = SCHEMA_VERSION if header == FIELDS else "1"
                projections = tuple(field for field in PROJECTIONS if field in header)
        if not rows:
            raise ValueError("ledger metadata is missing")
        for index, row in enumerate(rows, 1):
            if (set(row) != set(header) or row["schema_version"] != version
                    or row["sequence"] != str(index) or row["user_id"] != self.user
                    or row["event_type"] not in EVENT_TYPES):
                raise ValueError("unsupported or corrupt ledger event")
            try:
                parsed = datetime.fromisoformat(row["timestamp"])
                if parsed.tzinfo is None:
                    raise ValueError()
                data = json.loads(row["data"])
                if not isinstance(data, dict):
                    raise ValueError()
                projected = _projection(data)
                if any(projected[field] != row[field] for field in projections):
                    raise ValueError()
                # Normalize only in memory; the next successful mutation commits
                # schema 2 atomically without rewriting historical event data.
                row.update(schema_version=SCHEMA_VERSION, **projected, data=data)
            except (TypeError, ValueError, AttributeError):
                raise ValueError("corrupt ledger timestamp, projections or event data") from None
        metadata_policy = rows[0]["data"].get("policy_version")
        policy(metadata_policy)
        metadata = rows[0]["data"]
        bound = metadata.get("root")
        if (rows[0]["event_type"] != "metadata" or not isinstance(bound, str)
                or not os.path.isabs(bound) or os.path.normpath(bound) != bound
                or metadata != {"root": bound, "user_id": self.user, "policy_version": metadata_policy}):
            raise ValueError("ledger project, user or policy binding mismatch")
        for row in rows[1:]:
            if row["event_type"] == "metadata":
                raise ValueError("duplicate ledger metadata")
            if row["event_type"] == "relocation":
                data = row["data"]
                target = data.get("to_root")
                if (set(data) != {"from_root", "to_root"} or data["from_root"] != bound
                        or not isinstance(target, str) or not os.path.isabs(target)
                        or os.path.normpath(target) != target or target == bound):
                    raise ValueError("invalid ledger relocation")
                bound = target
        if bound != (str(self.root) if expected_root is None else expected_root):
            raise ValueError("ledger project, user or policy binding mismatch")
        return rows

    def _append(self, rows, event_type, data):
        rows.append(dict(schema_version=SCHEMA_VERSION, sequence=str(len(rows) + 1),
                         timestamp=_now(), event_type=event_type, user_id=self.user,
                         **_projection(data), data=data))

    def _initialize(self, rows):
        if not rows:
            self._append(rows, "metadata", {"root": str(self.root), "user_id": self.user,
                                            "policy_version": POLICY_VERSION})

    def _commit(self, rows, root_fd=None):
        if not isinstance(root_fd, _Access):
            with self._transaction(root_fd) as access:
                return self._commit(rows, access)
        access = root_fd
        self._safe_paths()
        self._check_access(access)
        if not access.directory_present:
            directory = self.directory.name if access.root_fd is not None else self.directory
            try:
                os.mkdir(directory, mode=0o700, dir_fd=access.root_fd)
            except FileExistsError:
                raise ValueError("ledger directory appeared during transaction") from None
            self._bind_directory(access)
            try:
                ledger = self.path.name if access.directory_fd is not None else self.path
                os.stat(ledger, dir_fd=access.directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise ValueError("ledger appeared before initial directory binding")
        self._check_access(access)
        if not access.ledger_present and access.root_fd is not None:
            # Sync the ledger directory's parent before first publication, also
            # when retrying after an earlier attempt left an empty directory.
            os.fsync(access.root_fd)
        with nullcontext(access.directory_fd) as directory_fd:
            if directory_fd is None:
                descriptor, temporary = tempfile.mkstemp(prefix=".pending-", dir=self.directory)
            else:
                temporary = ".pending-" + uuid.uuid4().hex
                descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                                     0o600, dir_fd=directory_fd)
            try:
                with os.fdopen(descriptor, "w", newline="", encoding="utf-8") as stream:
                    _write_ledger_csv(stream, rows)
                    stream.flush()
                    os.fsync(stream.fileno())
                self._check_access(access)
                if not access.ledger_present:
                    # Publish a complete first ledger without replacing any entry
                    # that appeared after the missing read, including a symlink.
                    if directory_fd is not None:
                        os.link(temporary, self.path.name, src_dir_fd=directory_fd,
                                dst_dir_fd=directory_fd, follow_symlinks=False)
                    elif sys.platform == "win32":
                        # Windows rename fails if the destination already exists.
                        os.rename(temporary, self.path)
                    else:
                        raise OSError("atomic no-replace ledger publication unavailable")
                elif directory_fd is None:
                    os.replace(temporary, self.path)
                else:
                    os.replace(temporary, self.path.name,
                               src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
                if directory_fd is not None:
                    os.fsync(directory_fd)
                    access.namespace_confirmed = True
            finally:
                try:
                    if directory_fd is None:
                        os.unlink(temporary)
                    else:
                        os.unlink(temporary, dir_fd=directory_fd)
                except FileNotFoundError:
                    pass
        self._check_access(access)

    def _confirm_mutation_namespace(self, access):
        """Confirm a no-op retry's namespace before acknowledging success."""
        if not access.namespace_confirmed and access.directory_fd is not None:
            self._check_access(access)
            os.fsync(access.directory_fd)
            access.namespace_confirmed = True
        self._check_access(access)

    def _state(self, rows):
        active = rows[0]["data"]["policy_version"] if rows else POLICY_VERSION
        state = dict(sessions={}, tracks={}, runs={}, assessments={}, executions=set(),
                     imports=set(), policy_version=active, windows={}, lineage_totals={}, epochs={},
                     session_generations={})
        try:
            for index, row in enumerate(rows[1:], 1):
                data, event = row["data"], row["event_type"]
                if event == "session":
                    _string(data["session"], "stored session")
                    if type(data["enabled"]) is not bool:
                        raise ValueError("invalid enabled state")
                    _string(data["generation"], "stored generation")
                    previous = state["sessions"].get(data["session"])
                    generations = state["session_generations"].setdefault(data["session"], set())
                    if ((previous is not None and previous["enabled"] == data["enabled"])
                            or data["generation"] in generations):
                        raise ValueError("invalid stored session transition")
                    generations.add(data["generation"])
                    state["sessions"][data["session"]] = data
                elif event == "policy_adoption":
                    target = {LEGACY_POLICY_VERSION: SECOND_POLICY_VERSION,
                              SECOND_POLICY_VERSION: THIRD_POLICY_VERSION,
                              THIRD_POLICY_VERSION: POLICY_VERSION}.get(state["policy_version"])
                    if data != {"from_policy_version": state["policy_version"], "to_policy_version": target} or target is None:
                        raise ValueError("invalid policy adoption")
                    previous = state["policy_version"]
                    state["policy_version"] = target
                    state["tracks"] = {key: track for key, track in state["tracks"].items()
                                       if policy_lineage(previous, track["role"], track["platform"]) ==
                                          policy_lineage(target, track["role"], track["platform"])}
                elif event == "transition":
                    version = data.get("policy_version", state["policy_version"])
                    if version != state["policy_version"]:
                        raise ValueError("transition policy differs from active policy")
                    ladders, _ = policy(version)
                    recommend({"track": data, "available_steps": data["available_steps"],
                               "assessments": [], "policy_version": version,
                               "advice_level": data.get("advice_level", "medium")})
                    if data["role"] == "advisor" and version in (THIRD_POLICY_VERSION, POLICY_VERSION):
                        if type(data["context_floor"]) is not int or data["context_floor"] != ADVICE_FLOORS[data["advice_level"]] or data["step"] < data["context_floor"]:
                            raise ValueError("invalid stored Advisor context floor")
                    if ladders[(data["platform"], data["role"])][data["step"]] != (data["family"], data["effort"]):
                        raise ValueError("invalid stored transition rung")
                    self._validate_transition(rows, index, data, state, version, ladders)
                    state["tracks"][_key(data)] = dict(data, policy_version=version)
                elif event == "advisor_context":
                    track = state["tracks"][_key(data)]
                    if (state["policy_version"] not in (THIRD_POLICY_VERSION, POLICY_VERSION)
                            or track["role"] != "advisor" or track["epoch"] != data["epoch"]
                            or track.get("advice_level") == data["advice_level"]
                            or type(data["context_floor"]) is not int
                            or data["context_floor"] != ADVICE_FLOORS[data["advice_level"]]
                            or track["step"] < data["context_floor"]):
                        raise ValueError("invalid Advisor context update")
                    track.update(advice_level=data["advice_level"], context_floor=data["context_floor"])
                elif event == "launch":
                    run_id = data["run_id"]
                    if run_id in state["runs"]:
                        raise ValueError("duplicate stored run")
                    track = state["tracks"][_key(data)]
                    if track["epoch"] != data["epoch"]:
                        raise ValueError("launch without current epoch")
                    if type(data["step"]) is not int or any(data[field] != track[field] for field in ("step", "family", "effort", "model_id", "reason", "previous_epoch")):
                        raise ValueError("launch settings differ from epoch")
                    run_policy = data.get("policy_version", track["policy_version"])
                    if policy_lineage(run_policy, data["role"], data["platform"]) != policy_lineage(track["policy_version"], track["role"], track["platform"]):
                        raise ValueError("launch policy differs from epoch")
                    if data["role"] == "advisor" and run_policy in (THIRD_POLICY_VERSION, POLICY_VERSION):
                        if (type(data["context_floor"]) is not int or data["context_floor"] != ADVICE_FLOORS[data["advice_level"]]
                                or data["context_floor"] != track["context_floor"]
                                or data["advice_level"] != track["advice_level"]):
                            raise ValueError("launch Advisor context differs from prepared context")
                    self._validate_launch(data, state, run_policy)
                    state["runs"][run_id] = dict(data, policy_version=run_policy)
                    track.update(models=data["models"], available_steps=data["available_steps"])
                elif event == "assessment":
                    request = data["request"]
                    _validate_assessment_request(request)
                    run_id = request["run_id"]
                    if run_id not in state["runs"] or run_id in state["assessments"]:
                        raise ValueError("invalid stored assessment run")
                    run = state["runs"][run_id]
                    _validate_fields(data["attribution"], policy(run["policy_version"])[0])
                    if type(data["result"]["eligible"]) is not bool:
                        raise ValueError("invalid stored assessment eligibility")
                    expected = {field: run[field] for field in
                                ("platform", "role", "tier", "step", "model_id", "epoch")}
                    expected.update(run_id=run_id, score=request["score"],
                                    timestamp=data["attribution"]["timestamp"],
                                    verified=not self._exclusions(run, request, state))
                    if "policy_version" in data["attribution"]:
                        expected["policy_version"] = run["policy_version"]
                    if expected != data["attribution"]:
                        raise ValueError("corrupt stored assessment attribution")
                    if (data["result"]["eligible"] != expected["verified"]
                            or data["result"]["exclusions"] != self._exclusions(run, request, state)
                            or data["result"]["run_id"] != run_id):
                        raise ValueError("corrupt stored assessment result")
                    self._ingest_assessment(state, dict(
                        data, attribution=dict(expected, policy_version=run["policy_version"])))
                    self._validate_assessment_transition(rows, index, data, run, state, expected["verified"])
                    state["executions"].add((run["platform"], request["execution_id"]))
                elif event == "legacy_import":
                    _, digest = _legacy_payload(data["rows"])
                    if digest != data["digest"] or digest in state["imports"]:
                        raise ValueError("invalid legacy import digest")
                    state["imports"].add(digest)
        except (KeyError, TypeError, IndexError):
            raise ValueError("corrupt ledger event structure") from None
        return state

    def _validate_launch(self, data, state, run_policy):
        for field in ("run_id", "session", "user_id", "session_generation"):
            _string(data[field], "stored " + field)
        session = state["sessions"].get(data["session"], {})
        if (data["user_id"] != self.user or not session.get("enabled", False)
                or data["session_generation"] != session.get("generation")):
            raise ValueError("invalid stored launch provenance")
        _validate_mode(data["platform"], data["mode"])
        validation = dict(track=data, available_steps=data["available_steps"],
                          assessments=[], policy_version=run_policy,
                          advice_level=data.get("advice_level", "medium"))
        _validate_capabilities(validation, data["models"])
        if (data["step"] not in data["available_steps"]
                or data["models"][data["family"]] != data["model_id"]):
            raise ValueError("stored launch does not match capabilities")
        if "consultation" in data:
            if data["role"] != "advisor" or run_policy not in (THIRD_POLICY_VERSION, POLICY_VERSION):
                raise ValueError("consultation context is Advisor-only")
            _validate_consultation(data["platform"], data["consultation"], data["advice_level"])

    def _validate_transition(self, rows, index, data, state, version, ladders):
        key = _key(data)
        previous = state["tracks"].get(key)
        epoch = data["epoch"]
        _string(epoch, "stored transition epoch")
        epochs = state["epochs"].setdefault(key, set())
        if epoch in epochs:
            raise ValueError("transition epoch is not fresh")
        epochs.add(epoch)

        models, available = data["models"], data["available_steps"]
        if not isinstance(models, dict):
            raise ValueError("invalid stored models")
        for step in available:
            family = ladders[(data["platform"], data["role"])][step][0]
            _string(models[family], "stored exact model ID")
        if data["model_id"] != models[data["family"]]:
            raise ValueError("stored model does not match resolved family")

        # Assessment transitions were checked against the immediately preceding
        # assessment, including its run-specific Advisor floor.
        prior = rows[index - 1] if index else None
        if prior and prior["event_type"] == "assessment" and prior["data"]["result"]["transition"] is not None:
            return

        role, platform, tier = data["role"], data["platform"], data["tier"]
        advice_level = data.get("advice_level", "medium")
        _, floors = policy(version)
        floor = (ADVICE_FLOORS[advice_level] if role == "advisor" else floors[platform][tier])
        provisional = dict(platform=platform, role=role, tier=tier, step=floor,
                           model_id="validation", epoch="validation")
        validation = dict(track=provisional, available_steps=available, assessments=[],
                          policy_version=version, advice_level=advice_level)
        if previous is None:
            selection = recommend(validation)
            step, reason = selection["selected_step"], "initial"
        elif role == "advisor" and previous["step"] < floor:
            selection = recommend(dict(validation, track=previous))
            step, reason = selection["selected_step"], "context_floor_raised"
        elif previous["step"] in available and models[previous["family"]] != previous["model_id"]:
            step, reason = previous["step"], "model_version_changed"
        else:
            selection = self._recommend(previous, state, available, advice_level)
            if not selection["reset_required"]:
                raise ValueError("unexpected standalone transition")
            step, reason = selection["selected_step"], selection["reason"]
        expected = self._transition_payload(platform, role, tier, step, models, available,
                                            reason, previous, version, advice_level, epoch)
        if "policy_version" not in data:
            del expected["policy_version"]
        if _json(data) != _json(expected):
            raise ValueError("corrupt standalone transition payload")

    def _validate_assessment_transition(self, rows, index, data, run, state, eligible):
        track = state["tracks"].get(_key(run))
        selection = None
        if eligible and track is not None and track["epoch"] == run["epoch"]:
            selection = self._recommend(track, state, advice_level=run.get("advice_level"))
        stored = data["result"]["transition"]
        if not selection or not selection["reset_required"]:
            if stored is not None:
                raise ValueError("unexpected assessment transition")
            return
        following = rows[index + 1] if index + 1 < len(rows) else None
        if (not isinstance(stored, dict) or following is None
                or following["event_type"] != "transition" or _json(stored) != _json(following["data"])):
            raise ValueError("corrupt assessment transition event")
        epoch = stored["epoch"]
        _string(epoch, "stored transition epoch")
        if epoch == track["epoch"]:
            raise ValueError("assessment transition epoch is not fresh")
        expected = self._transition_payload(
            run["platform"], run["role"], run["tier"], selection["selected_step"],
            track["models"], track["available_steps"], selection["reason"], track,
            state["policy_version"], run.get("advice_level", "medium"), epoch)
        if "policy_version" not in stored:
            del expected["policy_version"]
        if _json(stored) != _json(expected):
            raise ValueError("corrupt assessment transition payload")

    def _ingest_assessment(self, state, data):
        record = data["attribution"]
        version = record["policy_version"]
        ladders, _ = policy(version)
        timestamp = _validate_fields(record, ladders)
        lineage = policy_lineage(version, record["role"], record["platform"])
        sequence = len(state["assessments"])
        state["assessments"][record["run_id"]] = data
        totals = state["lineage_totals"]
        totals[lineage] = totals.get(lineage, 0) + 1
        if record["verified"]:
            key = (lineage, *(record[field] for field in _TRACK_FIELDS))
            window = state["windows"].setdefault(key, {"count": 0, "records": []})
            window["count"] += 1
            window["records"].append((timestamp, sequence, record))
            window["records"].sort(key=lambda item: (item[0], item[1]))
            del window["records"][:-5]

    def _recommend(self, track, state, available=None, advice_level=None):
        version = track["policy_version"]
        lineage = policy_lineage(version, track["role"], track["platform"])
        key = (lineage, *(track[field] for field in _TRACK_FIELDS))
        window = state["windows"].get(key, {"count": 0, "records": []})
        result = recommend({"track": track, "policy_version": version,
                            "advice_level": advice_level or track.get("advice_level", "medium"),
                            "available_steps": track["available_steps"] if available is None else available,
                            "assessments": [item[2] for item in window["records"]]})
        result["eligible_count"] = window["count"]
        result["excluded_count"] = state["lineage_totals"].get(lineage, 0) - window["count"]
        return result

    def _status(self, session, state):
        tracks = []
        for _, track in sorted(state["tracks"].items()):
            result = self._recommend(track, state)
            tracks.append(dict(track, eligible_count=result["eligible_count"],
                               window_run_ids=result["window_run_ids"], average=result["average"]))
        return dict(enabled=state["sessions"].get(session, {}).get("enabled", False),
                    session=session, user_id=self.user, root=str(self.root), ledger=str(self.path),
                    policy_version=state["policy_version"], tracks=tracks,
                    execution_contract=execution_contract(state["sessions"].get(session, {}).get("enabled", False)))

    def relocate(self, from_root):
        """Record an explicitly verified project move without rewriting history."""
        if (not isinstance(from_root, str) or not os.path.isabs(from_root)
                or os.path.normpath(from_root) != from_root or from_root == str(self.root)):
            raise ValueError("from_root must be a different absolute normalized path")
        with self._locked() as root_fd:
            rows = self._load(root_fd, from_root)
            if not rows:
                raise ValueError("ledger metadata is missing")
            self._state(rows)
            self._append(rows, "relocation", {"from_root": from_root, "to_root": str(self.root)})
            self._commit(rows, root_fd)
        return {"from_root": from_root, "to_root": str(self.root)}

    def status(self, session):
        _string(session, "session")
        with self._locked() as root_fd:
            return self._status(session, self._state(self._load(root_fd)))

    def set_enabled(self, session, enabled, platform=None, complexity=None, native_context=None, instruction_context=None):
        _string(session, "session")
        if type(enabled) is not bool:
            raise ValueError("enabled must be a boolean")
        if native_context is not None and (not enabled or platform is None):
            raise ValueError("native_context requires on and an explicit platform")
        if instruction_context is not None and not enabled:
            raise ValueError("instruction_context requires on")
        suggestions = None
        if enabled:
            platforms = ("claude", "codex") if platform is None else (platform,)
            suggestions = dict(applied=False, recommendations=[dict(
                platform=item, **orchestrator_recommendation(item, complexity, native_context)) for item in platforms])
            instruction_audit = audit_instructions(platform, instruction_context)
        with self._locked() as root_fd:
            rows = self._load(root_fd)
            state = self._state(rows)
            if state["sessions"].get(session, {}).get("enabled") != enabled:
                self._initialize(rows)
                self._append(rows, "session", dict(session=session, enabled=enabled, generation=uuid.uuid4().hex))
                self._commit(rows, root_fd)
                state = self._state(rows)
            result = self._status(session, state)
            if suggestions is not None:
                result["orchestrator_suggestion"] = suggestions
                result["instruction_audit"] = instruction_audit
            self._confirm_mutation_namespace(root_fd)
            return result

    def _transition_payload(self, platform, role, tier, step, models, available, reason, previous,
                            policy_version, advice_level, epoch):
        ladders, _ = policy(policy_version)
        family, effort = ladders[(platform, role)][step]
        track = dict(platform=platform, role=role, tier=tier, step=step, family=family,
                     effort=effort, model_id=models[family], epoch=epoch,
                     models=models, available_steps=available, reason=reason,
                     previous_epoch=previous["epoch"] if previous else None, policy_version=policy_version)
        if role == "advisor" and policy_version in (THIRD_POLICY_VERSION, POLICY_VERSION):
            track.update(advice_level=advice_level, context_floor=ADVICE_FLOORS[advice_level])
        return track

    def _transition(self, rows, platform, role, tier, step, models, available, reason, previous=None,
                    policy_version=POLICY_VERSION, advice_level="medium"):
        track = self._transition_payload(platform, role, tier, step, models, available, reason,
                                         previous, policy_version, advice_level, uuid.uuid4().hex)
        self._append(rows, "transition", track)
        return track

    def _adopt_policy(self, rows, state):
        current = state["policy_version"]
        changed = current != POLICY_VERSION
        while current != POLICY_VERSION:
            target = {LEGACY_POLICY_VERSION: SECOND_POLICY_VERSION,
                      SECOND_POLICY_VERSION: THIRD_POLICY_VERSION,
                      THIRD_POLICY_VERSION: POLICY_VERSION}[current]
            self._append(rows, "policy_adoption", {
                "from_policy_version": current, "to_policy_version": target})
            current = target
        return changed

    def adopt_policy(self):
        """Atomically adopt the current policy without inventing model IDs/runs."""
        with self._locked() as root_fd:
            rows = self._load(root_fd)
            state = self._state(rows)
            changed = not rows or self._adopt_policy(rows, state)
            self._initialize(rows)
            if changed:
                self._commit(rows, root_fd)
            self._confirm_mutation_namespace(root_fd)
            return dict(changed=changed, policy_version=POLICY_VERSION)

    def prepare(self, session, platform, role, tier=None, models=None, available_steps=None,
                mode="direct", advice_level=None, purpose=None, complexity=None, needed=False):
        """Reserve settings; purpose/complexity optionally enforce consultation policy."""
        _string(session, "session")
        if platform not in ("codex", "claude") or role not in ("executor", "advisor"):
            raise ValueError("invalid platform or role")
        consultation = None
        if role == "advisor":
            if tier is not None:
                raise ValueError("advisor has no complexity tier; omit it or use null")
            if type(needed) is not bool:
                raise ValueError("needed must be a boolean")
            if purpose is None and (complexity is not None or needed):
                raise ValueError("purpose is required when supplying Advisor task context")
            if advice_level is not None and (not isinstance(advice_level, str) or advice_level not in ADVICE_FLOORS):
                raise ValueError("advice_level must be medium, high, or super_high")
            if purpose is not None:
                consultation = advisor_context(platform, complexity, purpose, needed)
                if not consultation["consult"]:
                    raise ValueError("Advisor consultation is not allowed or requested for this context")
                if advice_level is not None and (advice_level not in ADVICE_FLOORS
                        or ADVICE_FLOORS[advice_level] < consultation["starting_step"]):
                    raise ValueError("advice_level cannot lower the required consultation floor")
                advice_level = advice_level or consultation["advice_level"]
                consultation = dict(consultation, purpose=purpose, complexity=complexity, needed=needed)
            advice_level = "medium" if advice_level is None else advice_level
            if not isinstance(advice_level, str) or advice_level not in ADVICE_FLOORS:
                raise ValueError("advice_level must be medium, high, or super_high")
            if consultation is not None:
                _validate_consultation(platform, consultation, advice_level)
        else:
            if tier not in ("low", "medium", "high", "business_doc"):
                raise ValueError("invalid executor tier")
            if advice_level is not None or purpose is not None or complexity is not None or needed:
                raise ValueError("consultation context is Advisor-only")
        _validate_mode(platform, mode)
        ladder = _LADDERS[(platform, role)]
        floor = ADVICE_FLOORS[advice_level] if role == "advisor" else _FLOORS[platform][tier]
        provisional = dict(platform=platform, role=role, tier=tier, step=floor,
                           model_id="validation", epoch="validation")
        validation = dict(track=provisional, available_steps=available_steps, assessments=[])
        if role == "advisor":
            validation["advice_level"] = advice_level
        _validate_capabilities(validation, models)
        models = json.loads(_json(models))
        available_steps = list(available_steps)
        with self._locked() as root_fd:
            rows = self._load(root_fd)
            state = self._state(rows)
            session_state = state["sessions"].get(session, {})
            if not session_state.get("enabled", False):
                raise ValueError("session is disabled; enable it before preparing runs")
            self._initialize(rows)
            if self._adopt_policy(rows, state):
                state = self._state(rows)
            track = state["tracks"].get((platform, role, tier))
            if track is None:
                selection = recommend(validation)
                track = self._transition(rows, platform, role, tier, selection["selected_step"],
                                         models, available_steps, "initial", advice_level=advice_level)
            elif role == "advisor" and track["step"] < floor:
                # A context increase starts clean before any old-rung window acts.
                selection = recommend(dict(validation, track=track))
                track = self._transition(rows, platform, role, tier, selection["selected_step"], models,
                                         available_steps, "context_floor_raised", track, advice_level=advice_level)
            elif (track["step"] in available_steps and models[track["family"]] != track["model_id"]):
                track = self._transition(rows, platform, role, tier, track["step"], models,
                                         available_steps, "model_version_changed", track, advice_level=advice_level)
            else:
                selection = self._recommend(track, state, available_steps, advice_level)
                if selection["reset_required"]:
                    track = self._transition(rows, platform, role, tier, selection["selected_step"],
                                             models, available_steps, selection["reason"], track,
                                             advice_level=advice_level)
            if role == "advisor" and track["advice_level"] != advice_level:
                context = dict(platform=platform, role=role, tier=None, epoch=track["epoch"],
                               advice_level=advice_level, context_floor=floor)
                self._append(rows, "advisor_context", context)
                track = dict(track, advice_level=advice_level, context_floor=floor)
            family, effort = ladder[track["step"]]
            run = dict(track, run_id=uuid.uuid4().hex, session=session, user_id=self.user,
                       session_generation=session_state["generation"], mode=mode, family=family,
                       effort=effort, models=models, available_steps=available_steps,
                       policy_version=state["policy_version"])
            if consultation is not None:
                run["consultation"] = consultation
            self._append(rows, "launch", run)
            self._commit(rows, root_fd)
            return run

    def _exclusions(self, run, request, state):
        session = state["sessions"].get(run["session"], {})
        exclusions = []
        if not request["verified"]:
            exclusions.append("unverified")
        if policy_lineage(run["policy_version"], run["role"], run["platform"]) != policy_lineage(state["policy_version"], run["role"], run["platform"]):
            exclusions.append("policy_changed")
        if (request["effective_model_id"] != run["model_id"]
                or request["effective_effort"] != run["effort"]):
            exclusions.append("receipt_mismatch")
        if (run["platform"], request["execution_id"]) in state["executions"]:
            exclusions.append("duplicate_execution")
        if not session.get("enabled") or session.get("generation") != run["session_generation"]:
            exclusions.append("session_disabled_or_changed")
        return exclusions

    def assess(self, run_id, score, effective_model_id, effective_effort, execution_id, verified):
        """Record the trusted host's review and actual execution receipt.

        verified=True attests independent review provenance, which this engine
        cannot inspect. Substituted, unverified, disabled or cached executions
        remain historical outcomes and never enter performance windows.
        """
        request = dict(run_id=run_id, score=score, effective_model_id=effective_model_id,
                       effective_effort=effective_effort, execution_id=execution_id, verified=verified)
        _validate_assessment_request(request)
        with self._locked() as root_fd:
            rows = self._load(root_fd)
            state = self._state(rows)
            if run_id not in state["runs"]:
                raise ValueError("unknown run_id")
            previous = state["assessments"].get(run_id)
            if previous:
                if previous["request"] != request:
                    raise ValueError("run is already assessed with a different outcome")
                self._confirm_mutation_namespace(root_fd)
                return previous["result"]
            run = state["runs"][run_id]
            exclusions = self._exclusions(run, request, state)
            eligible = not exclusions
            attribution = {key: run[key] for key in ("platform", "role", "tier", "step", "model_id", "epoch")}
            attribution.update(run_id=run_id, timestamp=_now(), score=score, verified=eligible,
                               policy_version=run["policy_version"])
            result = dict(run_id=run_id, eligible=eligible, exclusions=exclusions, transition=None)
            data = dict(request=request, result=result, attribution=attribution)
            self._append(rows, "assessment", data)
            self._ingest_assessment(state, data)
            track = state["tracks"].get(_key(run))
            if eligible and track is not None and track["epoch"] == run["epoch"]:
                selection = self._recommend(track, state, advice_level=run.get("advice_level"))
                if selection["reset_required"]:
                    result["transition"] = self._transition(
                        rows, run["platform"], run["role"], run["tier"], selection["selected_step"],
                        track["models"], track["available_steps"], selection["reason"], track,
                        policy_version=state["policy_version"],
                        advice_level=run.get("advice_level", "medium"))
            self._commit(rows, root_fd)
            return result

    def import_history(self, rows):
        """Preserve legacy rows losslessly without inventing live attribution."""
        payload, digest = _legacy_payload(rows)
        with self._locked() as root_fd:
            events = self._load(root_fd)
            state = self._state(events)
            duplicate = digest in state["imports"]
            if not duplicate:
                self._initialize(events)
                self._append(events, "legacy_import", dict(digest=digest, rows=json.loads(payload)))
                self._commit(events, root_fd)
            self._confirm_mutation_namespace(root_fd)
            return dict(imported_count=0 if duplicate else len(rows), duplicate=duplicate, eligible=False)


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main(argv=None):
    parser = _Parser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--platform", choices=("claude", "codex"))
    parser.add_argument("--complexity", choices=("low", "medium", "high", "super_high"))
    parser.add_argument("--native-context", help="JSON object describing current native mode and settings")
    parser.add_argument("--instruction-context", help="JSON object describing host instruction context")
    parser.add_argument("command", choices=("status", "on", "off", "prepare", "assess", "import-history", "adopt-policy", "relocate"))
    parser.add_argument("request", nargs="?")
    try:
        arguments = parser.parse_args(argv)
        engine = Engine(arguments.root, arguments.user)
        command = arguments.command
        if arguments.native_context is not None and command != "on":
            raise ValueError("--native-context is only valid for on")
        native_context = json.loads(arguments.native_context) if arguments.native_context is not None else None
        if arguments.native_context is not None and not isinstance(native_context, dict):
            raise ValueError("--native-context must be a JSON object")
        if arguments.instruction_context is not None and command != "on":
            raise ValueError("--instruction-context is only valid for on")
        instruction_context = json.loads(arguments.instruction_context) if arguments.instruction_context is not None else None
        if arguments.instruction_context is not None and not isinstance(instruction_context, dict):
            raise ValueError("--instruction-context must be a JSON object")
        if command == "adopt-policy":
            if arguments.request is not None:
                raise ValueError("adopt-policy does not accept a request file")
            result = engine.adopt_policy()
        elif command in ("status", "on", "off"):
            if arguments.request is not None:
                raise ValueError("this command does not accept a request file")
            result = (engine.status(arguments.session) if command == "status"
                      else engine.set_enabled(arguments.session, command == "on",
                                              platform=arguments.platform, complexity=arguments.complexity,
                                              native_context=native_context, instruction_context=instruction_context))
        else:
            if arguments.request is None:
                raise ValueError("this command requires a JSON request file")
            request = json.loads(Path(arguments.request).read_text(encoding="utf-8"))
            if not isinstance(request, dict):
                raise ValueError("request must be an object")
            if command == "relocate":
                result = engine.relocate(**request)
            elif command == "prepare":
                result = engine.prepare(session=arguments.session, **request)
            elif command == "assess":
                result = engine.assess(**request)
            else:
                result = engine.import_history(**request)
    except (OSError, UnicodeError, ValueError, TypeError, NotImplementedError, csv.Error) as error:
        print("error: " + " ".join(str(error).splitlines()), file=sys.stderr)
        return 1
    print(_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
