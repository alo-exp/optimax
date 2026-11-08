"""Stdlib controller for one canonical project and explicit user.

All durable state is one versioned CSV. flock on the project directory (POSIX)
or msvcrt locking on a per-project file in the temp directory (Windows)
serializes cooperating controllers; fsync and atomic rename publish updates
without lock or state sidecars in the project. Requires a local filesystem;
network filesystems are unsupported. The trusted host resolves exact model IDs, discovers supported
rungs, dispatches natively, and independently reviews actual execution receipts.
This engine never launches agents or changes native/global model settings.

adopt_policy() or the first successful prepare appends ordered v1-to-v2-to-v3
policy events. Historical rows retain their original ordinal semantics. V2
retires old Executor tracks; v3 preserves their compatible epochs/windows and
retires old Advisor tracks. New Advisors carry per-consultation advice levels,
not complexity tiers. Assessments apply each prepared run's contextual floor.
Status never adopts. Explicit on returns unapplied orchestrator suggestions.
"""
import argparse
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
try:
    import fcntl
except ImportError:  # Windows: lock a per-project file in the temp dir instead
    fcntl = None
    import msvcrt
    import time
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import uuid

try:
    from .ladder import (_FLOORS, _LADDERS, ADVICE_FLOORS, LEGACY_POLICY_VERSION,
                         SECOND_POLICY_VERSION, POLICY_VERSION, policy, policy_lineage, recommend)
    from .session_policy import advisor_context, orchestrator_recommendation
except ImportError:
    from ladder import (_FLOORS, _LADDERS, ADVICE_FLOORS, LEGACY_POLICY_VERSION,
                        SECOND_POLICY_VERSION, POLICY_VERSION, policy, policy_lineage, recommend)
    from session_policy import advisor_context, orchestrator_recommendation

SCHEMA_VERSION = "2"
PROJECTIONS = ("platform", "role", "tier", "run_id", "epoch")
FIELDS = ("schema_version", "sequence", "timestamp", "event_type", "user_id", *PROJECTIONS, "data")
LEGACY_FIELDS = tuple(field for field in FIELDS if field != "tier")
EVENT_TYPES = {"metadata", "session", "transition", "launch", "assessment", "legacy_import", "policy_adoption", "advisor_context"}


def _string(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 4096:
        raise ValueError(label + " must be a nonempty string of at most 4096 characters")


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _key(track):
    return (track["platform"], track["role"], track["tier"])


def _projection(data):
    attribution = data.get("attribution", data)
    return {field: "" if attribution.get(field) is None else attribution[field]
            for field in PROJECTIONS}


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

    @contextmanager
    def _locked(self):
        if fcntl is None:
            with self._locked_windows():
                yield
            return
        descriptor = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            self._safe_paths()
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    @contextmanager
    def _locked_windows(self):
        # Directories cannot be opened or locked on Windows, and a sidecar in the
        # project would alter the ledger directory, so lock outside the project.
        digest = hashlib.sha256(str(self.root).lower().encode("utf-8")).hexdigest()[:32]
        lock_path = Path(tempfile.gettempdir()) / ("optimax-" + digest + ".lock")
        with open(lock_path, "a+b") as stream:
            while True:
                try:
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(0.05)
            try:
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

    def _load(self):
        if not self.path.exists():
            return []
        descriptor = os.open(self.path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(descriptor, "r", newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream, strict=True)
            header = tuple(reader.fieldnames or ())
            if header not in (FIELDS, LEGACY_FIELDS):
                raise ValueError("unsupported or corrupt ledger header")
            version = SCHEMA_VERSION if header == FIELDS else "1"
            projections = tuple(field for field in PROJECTIONS if field in header)
            rows = list(reader)
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
        expected = {"root": str(self.root), "user_id": self.user, "policy_version": metadata_policy}
        if rows[0]["event_type"] != "metadata" or rows[0]["data"] != expected:
            raise ValueError("ledger project, user or policy binding mismatch")
        if any(row["event_type"] == "metadata" for row in rows[1:]):
            raise ValueError("duplicate ledger metadata")
        return rows

    def _append(self, rows, event_type, data):
        rows.append(dict(schema_version=SCHEMA_VERSION, sequence=str(len(rows) + 1),
                         timestamp=_now(), event_type=event_type, user_id=self.user,
                         **_projection(data), data=data))

    def _initialize(self, rows):
        if not rows:
            self._append(rows, "metadata", {"root": str(self.root), "user_id": self.user,
                                            "policy_version": POLICY_VERSION})

    def _commit(self, rows):
        self._safe_paths()
        self.directory.mkdir(mode=0o700, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".pending-", dir=self.directory)
        try:
            with os.fdopen(descriptor, "w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(dict(row, data=_json(row["data"])) for row in rows)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            if fcntl is None:
                return  # Windows cannot open directories to fsync them
            directory_fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _state(self, rows):
        active = rows[0]["data"]["policy_version"] if rows else POLICY_VERSION
        state = dict(sessions={}, tracks={}, runs={}, assessments={}, executions=set(),
                     imports=set(), policy_version=active)
        try:
            for row in rows[1:]:
                data, event = row["data"], row["event_type"]
                if event == "session":
                    _string(data["session"], "stored session")
                    if type(data["enabled"]) is not bool:
                        raise ValueError("invalid enabled state")
                    _string(data["generation"], "stored generation")
                    state["sessions"][data["session"]] = data
                elif event == "policy_adoption":
                    target, retired_role = {
                        LEGACY_POLICY_VERSION: (SECOND_POLICY_VERSION, "executor"),
                        SECOND_POLICY_VERSION: (POLICY_VERSION, "advisor"),
                    }.get(state["policy_version"], (None, None))
                    if data != {"from_policy_version": state["policy_version"], "to_policy_version": target} or target is None:
                        raise ValueError("invalid policy adoption")
                    state["policy_version"] = target
                    state["tracks"] = {key: track for key, track in state["tracks"].items()
                                       if track["role"] != retired_role}
                elif event == "transition":
                    version = data.get("policy_version", state["policy_version"])
                    if version != state["policy_version"]:
                        raise ValueError("transition policy differs from active policy")
                    ladders, _ = policy(version)
                    recommend({"track": data, "available_steps": data["available_steps"],
                               "assessments": [], "policy_version": version,
                               "advice_level": data.get("advice_level", "medium")})
                    if data["role"] == "advisor" and version == POLICY_VERSION:
                        if data["context_floor"] != ADVICE_FLOORS[data["advice_level"]] or data["step"] < data["context_floor"]:
                            raise ValueError("invalid stored Advisor context floor")
                    if ladders[(data["platform"], data["role"])][data["step"]] != (data["family"], data["effort"]):
                        raise ValueError("invalid stored transition rung")
                    state["tracks"][_key(data)] = dict(data, policy_version=version)
                elif event == "advisor_context":
                    track = state["tracks"][_key(data)]
                    if (track["role"] != "advisor" or track["epoch"] != data["epoch"]
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
                    if any(data[field] != track[field] for field in ("step", "family", "effort", "model_id")):
                        raise ValueError("launch settings differ from epoch")
                    run_policy = data.get("policy_version", track["policy_version"])
                    if policy_lineage(run_policy, data["role"]) != policy_lineage(track["policy_version"], track["role"]):
                        raise ValueError("launch policy differs from epoch")
                    if data["role"] == "advisor" and run_policy == POLICY_VERSION:
                        if (data["context_floor"] != ADVICE_FLOORS[data["advice_level"]]
                                or data["context_floor"] != track["context_floor"]
                                or data["advice_level"] != track["advice_level"]):
                            raise ValueError("launch Advisor context differs from prepared context")
                    state["runs"][run_id] = dict(data, policy_version=run_policy)
                    track.update(models=data["models"], available_steps=data["available_steps"])
                elif event == "assessment":
                    request = data["request"]
                    run_id = request["run_id"]
                    if run_id not in state["runs"] or run_id in state["assessments"]:
                        raise ValueError("invalid stored assessment run")
                    run = state["runs"][run_id]
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
                    state["assessments"][run_id] = dict(
                        data, attribution=dict(expected, policy_version=run["policy_version"]))
                    state["executions"].add((run["platform"], request["execution_id"]))
                elif event == "legacy_import":
                    state["imports"].add(data["digest"])
                    if not isinstance(data["rows"], list):
                        raise ValueError("invalid legacy import")
        except (KeyError, TypeError, IndexError):
            raise ValueError("corrupt ledger event structure") from None
        return state

    def _recommend(self, track, state, available=None, advice_level=None):
        version = track["policy_version"]
        lineage = policy_lineage(version, track["role"])
        return recommend({"track": track, "policy_version": version,
                          "advice_level": advice_level or track.get("advice_level", "medium"),
                          "available_steps": track["available_steps"] if available is None else available,
                          "assessments": [data["attribution"] for data in state["assessments"].values()
                                          if policy_lineage(data["attribution"]["policy_version"],
                                                            data["attribution"]["role"]) == lineage]})

    def _status(self, session, state):
        tracks = []
        for _, track in sorted(state["tracks"].items()):
            result = self._recommend(track, state)
            tracks.append(dict(track, eligible_count=result["eligible_count"],
                               window_run_ids=result["window_run_ids"], average=result["average"]))
        return dict(enabled=state["sessions"].get(session, {}).get("enabled", False),
                    session=session, user_id=self.user, root=str(self.root), ledger=str(self.path),
                    policy_version=state["policy_version"], tracks=tracks)

    def status(self, session):
        _string(session, "session")
        with self._locked():
            return self._status(session, self._state(self._load()))

    def set_enabled(self, session, enabled, platform=None, complexity=None, native_context=None):
        _string(session, "session")
        if type(enabled) is not bool:
            raise ValueError("enabled must be a boolean")
        if native_context is not None and (not enabled or platform is None):
            raise ValueError("native_context requires on and an explicit platform")
        suggestions = None
        if enabled:
            platforms = ("claude", "codex") if platform is None else (platform,)
            suggestions = dict(applied=False, recommendations=[dict(
                platform=item, **orchestrator_recommendation(item, complexity, native_context)) for item in platforms])
        with self._locked():
            rows = self._load()
            state = self._state(rows)
            if state["sessions"].get(session, {}).get("enabled") != enabled:
                self._initialize(rows)
                self._append(rows, "session", dict(session=session, enabled=enabled, generation=uuid.uuid4().hex))
                self._commit(rows)
                state = self._state(rows)
            result = self._status(session, state)
            if suggestions is not None:
                result["orchestrator_suggestion"] = suggestions
            return result

    def _transition(self, rows, platform, role, tier, step, models, available, reason, previous=None,
                    policy_version=POLICY_VERSION, advice_level="medium"):
        ladders, _ = policy(policy_version)
        family, effort = ladders[(platform, role)][step]
        track = dict(platform=platform, role=role, tier=tier, step=step, family=family,
                     effort=effort, model_id=models[family], epoch=uuid.uuid4().hex,
                     models=models, available_steps=available, reason=reason,
                     previous_epoch=previous["epoch"] if previous else None, policy_version=policy_version)
        if role == "advisor" and policy_version == POLICY_VERSION:
            track.update(advice_level=advice_level, context_floor=ADVICE_FLOORS[advice_level])
        self._append(rows, "transition", track)
        return track

    def _adopt_policy(self, rows, state):
        current = state["policy_version"]
        changed = current != POLICY_VERSION
        while current != POLICY_VERSION:
            target = SECOND_POLICY_VERSION if current == LEGACY_POLICY_VERSION else POLICY_VERSION
            self._append(rows, "policy_adoption", {
                "from_policy_version": current, "to_policy_version": target})
            current = target
        return changed

    def adopt_policy(self):
        """Atomically adopt the current policy without inventing model IDs/runs."""
        with self._locked():
            rows = self._load()
            state = self._state(rows)
            changed = not rows or self._adopt_policy(rows, state)
            self._initialize(rows)
            if changed:
                self._commit(rows)
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
        else:
            if tier not in ("low", "medium", "high", "business_doc"):
                raise ValueError("invalid executor tier")
            if advice_level is not None or purpose is not None or complexity is not None or needed:
                raise ValueError("consultation context is Advisor-only")
        if mode not in ("direct", "codex-ultra", "claude-ultracode"):
            raise ValueError("invalid mode")
        if mode != "direct" and not mode.startswith(platform + "-"):
            raise ValueError("mode must match platform")
        ladder = _LADDERS[(platform, role)]
        floor = ADVICE_FLOORS[advice_level] if role == "advisor" else _FLOORS[platform][tier]
        provisional = dict(platform=platform, role=role, tier=tier, step=floor,
                           model_id="validation", epoch="validation")
        validation = dict(track=provisional, available_steps=available_steps, assessments=[])
        if role == "advisor":
            validation["advice_level"] = advice_level
        recommend(validation)
        if not isinstance(models, dict):
            raise ValueError("models must map logical family to resolved exact model ID")
        for step in available_steps:
            family = ladder[step][0]
            if family not in models:
                raise ValueError("models must resolve every available family")
            _string(models[family], "exact model ID")
        models = json.loads(_json(models))
        available_steps = list(available_steps)
        with self._locked():
            rows = self._load()
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
            self._commit(rows)
            return run

    def _exclusions(self, run, request, state):
        session = state["sessions"].get(run["session"], {})
        exclusions = []
        if not request["verified"]:
            exclusions.append("unverified")
        if policy_lineage(run["policy_version"], run["role"]) != policy_lineage(state["policy_version"], run["role"]):
            exclusions.append("policy_changed")
        if (request["effective_model_id"] != run["model_id"]
                or request["effective_effort"] != run["effort"]):
            exclusions.append("receipt_mismatch")
        if (run["platform"], request["execution_id"]) in state["executions"]:
            exclusions.append("duplicate_execution")
        if not session.get("enabled") or session.get("generation") != run["session_generation"]:
            exclusions.append("session_disabled_or_changed")
        return exclusions

    def assess(self, run_id, score, effective_model_id, effective_effort, execution_id, verified=True):
        """Record the trusted host's review and actual execution receipt.

        verified=True attests independent review provenance, which this engine
        cannot inspect. Substituted, unverified, disabled or cached executions
        remain historical outcomes and never enter performance windows.
        """
        for value, label in ((run_id, "run_id"), (effective_model_id, "effective_model_id"),
                             (effective_effort, "effective_effort"), (execution_id, "execution_id")):
            _string(value, label)
        if type(score) is not int or not 0 <= score <= 5:
            raise ValueError("score must be an integer from 0 to 5")
        if type(verified) is not bool:
            raise ValueError("verified must be a boolean")
        request = dict(run_id=run_id, score=score, effective_model_id=effective_model_id,
                       effective_effort=effective_effort, execution_id=execution_id, verified=verified)
        with self._locked():
            rows = self._load()
            state = self._state(rows)
            if run_id not in state["runs"]:
                raise ValueError("unknown run_id")
            previous = state["assessments"].get(run_id)
            if previous:
                if previous["request"] != request:
                    raise ValueError("run is already assessed with a different outcome")
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
            state["assessments"][run_id] = data
            track = state["tracks"].get(_key(run))
            if eligible and track is not None and track["epoch"] == run["epoch"]:
                selection = self._recommend(track, state, advice_level=run.get("advice_level"))
                if selection["reset_required"]:
                    result["transition"] = self._transition(
                        rows, run["platform"], run["role"], run["tier"], selection["selected_step"],
                        track["models"], track["available_steps"], selection["reason"], track,
                        policy_version=state["policy_version"],
                        advice_level=run.get("advice_level", "medium"))
            self._commit(rows)
            return result

    def import_history(self, rows):
        """Preserve legacy rows losslessly without inventing live attribution."""
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("legacy rows must be a list of objects")
        payload = _json(rows)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        with self._locked():
            events = self._load()
            state = self._state(events)
            duplicate = digest in state["imports"]
            if not duplicate:
                self._initialize(events)
                self._append(events, "legacy_import", dict(digest=digest, rows=json.loads(payload)))
                self._commit(events)
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
    parser.add_argument("command", choices=("status", "on", "off", "prepare", "assess", "import-history", "adopt-policy"))
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
                                              native_context=native_context))
        else:
            if arguments.request is None:
                raise ValueError("this command requires a JSON request file")
            request = json.loads(Path(arguments.request).read_text(encoding="utf-8"))
            if not isinstance(request, dict):
                raise ValueError("request must be an object")
            if command == "prepare":
                result = engine.prepare(session=arguments.session, **request)
            elif command == "assess":
                result = engine.assess(**request)
            else:
                result = engine.import_history(**request)
    except (OSError, UnicodeError, ValueError, TypeError, csv.Error) as error:
        print("error: " + " ".join(str(error).splitlines()), file=sys.stderr)
        return 1
    print(_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
