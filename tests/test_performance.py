"""Behavioral qualification for the durable per-user performance controller."""
import csv
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/optimax/scripts"))
from performance import Engine, recommend
from session_policy import advisor_context

MODELS = {"terra": "terra-v1", "sol": "sol-v1"}
CLAUDE_MODELS = {"haiku": "haiku-v1", "sonnet": "sonnet-v1", "opus": "opus-v1"}
SCRIPT = Path(__file__).resolve().parents[1] / "skills/optimax/scripts" / "performance.py"


def parallel_prepare(arguments):
    root, user, session = arguments
    return Engine(root, user).prepare(session, "codex", "executor", "low", MODELS, list(range(7)))


def parallel_assess(arguments):
    root, run = arguments
    return Engine(root, "actual-user").assess(
        run["run_id"], 4, run["model_id"], run["effort"], "exec-" + run["run_id"], verified=True)


def write_policy_one_fixture(engine, session):
    """Authentic v1 ordinal semantics: Codex medium means Sol High."""
    rows = []
    def append(kind, data):
        attribution = data.get("attribution", data)
        rows.append(dict(schema_version="2", sequence=str(len(rows) + 1),
                         timestamp=f"2026-11-07T00:00:{len(rows):02d}+00:00",
                         event_type=kind, user_id=engine.user,
                         **{field: attribution.get(field) or "" for field in
                            ("platform", "role", "tier", "run_id", "epoch")},
                         data=data))
    append("metadata", dict(root=str(engine.root), user_id=engine.user,
                            policy_version="optimal-ultra-ladder-v1"))
    append("session", dict(session=session, enabled=True, generation="legacy-generation"))
    executor = dict(platform="codex", role="executor", tier="medium", step=1,
                    family="sol", effort="high", model_id="sol-old", epoch="executor-v1",
                    models={"luna": "luna-old", "sol": "sol-old"}, available_steps=[0, 1, 2, 3],
                    reason="initial", previous_epoch=None)
    advisor = dict(platform="codex", role="advisor", tier=None, step=0,
                   family="sol", effort="xhigh", model_id="sol-old", epoch="advisor-v1",
                   models={"sol": "sol-old"}, available_steps=[0, 1],
                   reason="initial", previous_epoch=None)
    append("transition", executor)
    old_executor = dict(executor, run_id="executor-outstanding", session=session,
                        user_id=engine.user, session_generation="legacy-generation", mode="direct")
    append("launch", old_executor)
    append("transition", advisor)
    for index in range(4):
        run = dict(advisor, run_id=f"advisor-{index}", session=session,
                   user_id=engine.user, session_generation="legacy-generation", mode="direct")
        append("launch", run)
        if index < 3:
            request = dict(run_id=run["run_id"], score=4, effective_model_id="sol-old",
                           effective_effort="xhigh", execution_id=f"old-advisor-{index}", verified=True)
            attribution = {key: run[key] for key in ("platform", "role", "tier", "step", "model_id", "epoch")}
            attribution.update(run_id=run["run_id"], score=4, verified=True,
                               timestamp=f"2026-11-07T00:01:{index:02d}+00:00")
            append("assessment", dict(request=request, attribution=attribution,
                                      result=dict(run_id=run["run_id"], eligible=True, exclusions=[], transition=None)))
    engine.directory.mkdir()
    with engine.path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(dict(row, data=json.dumps(row["data"])) for row in rows)
    return old_executor


def write_policy_two_fixture(engine, session):
    write_policy_one_fixture(engine, session)
    with engine.path.open(newline="", encoding="utf-8") as stream:
        rows = [dict(row, data=json.loads(row["data"])) for row in csv.DictReader(stream)]
    rows[0]["data"]["policy_version"] = "optimal-ultra-ladder-v2"
    for row in rows:
        data = row["data"]
        if row["role"] == "executor":
            data.update(family="terra", effort="medium", model_id="terra-old",
                        models={"terra": "terra-old", "sol": "sol-old"}, available_steps=list(range(7)))
    executor = next(row["data"] for row in rows if row["run_id"] == "executor-outstanding")
    for index in range(3):
        run = dict(executor, run_id=f"executor-scored-{index}")
        attribution = {key: run[key] for key in ("platform", "role", "tier", "step", "model_id", "epoch")}
        attribution.update(run_id=run["run_id"], score=4, verified=True,
                           timestamp=f"2026-11-07T00:02:{index:02d}+00:00")
        request = dict(run_id=run["run_id"], score=4, effective_model_id=run["model_id"],
                       effective_effort=run["effort"], execution_id=f"v2-executor-{index}", verified=True)
        for kind, data in (("launch", run), ("assessment", dict(
                request=request, attribution=attribution,
                result=dict(run_id=run["run_id"], eligible=True, exclusions=[], transition=None)))):
            projected = data.get("attribution", data)
            rows.append(dict(schema_version="2", sequence=str(len(rows) + 1),
                             timestamp=f"2026-11-07T00:03:{len(rows):02d}+00:00",
                             event_type=kind, user_id=engine.user,
                             **{field: projected.get(field) or "" for field in
                                ("platform", "role", "tier", "run_id", "epoch")}, data=data))
    with engine.path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(dict(row, data=json.dumps(row["data"])) for row in rows)
    return executor


class PerformanceTests(unittest.TestCase):

    def test_legacy_import_rejects_nonstring_keys_at_every_depth_without_mutation(self):
        invalid = {
            "numeric_order": [{2: "a", 10: "b"}],
            "single_numeric": [{2: "a"}],
            "nested": [{"nested": {2: "a", 10: "b"}}],
            "array_nested": [{"nested": [{2: "a"}]}],
            "tuple_nested": [{"nested": ({2: "a"},)}],
            "collision": [{2: "a", "2": "b"}],
            "none_collision": [{None: "a", "null": "b"}],
            "boolean": [{True: "a"}],
            "float": [{2.5: "a"}],
            "nonfinite_key": [{float("inf"): "a"}],
        }
        for existing in (False, True):
            for case, rows in invalid.items():
                with self.subTest(existing=existing, case=case), tempfile.TemporaryDirectory() as root:
                    engine = Engine(root, "actual-user")
                    if existing:
                        engine.set_enabled(self.session, True)
                    before = engine.path.read_bytes() if existing else None
                    with self.assertRaisesRegex(ValueError, "keys must be strings"):
                        engine.import_history(rows)
                    self.assertEqual(engine.path.read_bytes() if engine.path.exists() else None, before)
                    self.assertEqual(engine.status(self.session)["enabled"], existing)
                    if engine.directory.exists():
                        self.assertEqual(list(engine.directory.iterdir()), [engine.path])

    def test_legacy_import_preserves_nonfinite_rejection_and_compatible_string_key_history(self):
        import hashlib
        nonfinite = [{"value": float("nan")}, {"nested": [float("inf")]},
                     {"nested": {"value": -float("inf")}}]
        self.enable()
        before = self.engine.path.read_bytes()
        for row in nonfinite:
            with self.subTest(row=row), self.assertRaises(ValueError):
                self.engine.import_history([row])
            self.assertEqual(self.engine.path.read_bytes(), before)
        cyclic = {"cycle": None}
        cyclic["cycle"] = cyclic
        with self.assertRaisesRegex(ValueError, "Circular reference"):
            self.engine.import_history([cyclic])
        self.assertEqual(self.engine.path.read_bytes(), before)
        # This is the persisted JSON of an older, valid single-numeric-key API import.
        old_payload = json.dumps([{2: "a"}], sort_keys=True, separators=(",", ":"), allow_nan=False)
        imported = json.loads(old_payload)
        self.engine.import_history(imported)
        event = self.events()[-1]
        self.assertEqual(event["data"]["digest"], hashlib.sha256(old_payload.encode("utf-8")).hexdigest())
        published = self.engine.path.read_bytes()
        restarted = Engine(self.root, "actual-user")
        self.assertTrue(restarted.status(self.session)["enabled"])
        self.assertTrue(restarted.import_history(imported)["duplicate"])
        self.assertEqual(restarted.path.read_bytes(), published)

    def test_cli_legacy_import_string_keys_remain_lossless_and_idempotent(self):
        rows = [{"2": "a", "10": "b", "nested": {"2": "c", "10": "d"}}]
        request = self.root / "legacy-request.json"
        request.write_text(json.dumps({"rows": rows}), encoding="utf-8")
        command = [sys.executable, str(SCRIPT), "--root", str(self.root), "--user",
                   "actual-user", "--session", self.session, "import-history", str(request)]
        result = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["imported_count"], 1)
        before = self.engine.path.read_bytes()
        self.assertEqual(self.engine._load()[-1]["data"]["rows"], rows)
        reordered = [{"nested": {"10": "d", "2": "c"}, "10": "b", "2": "a"}]
        self.assertTrue(self.engine.import_history(reordered)["duplicate"])
        self.assertEqual(self.engine.path.read_bytes(), before)

    def test_isolated_csv_reader_failures_preserve_history_and_close_descriptors(self):
        program = r"""
import csv
import json
import os
import subprocess
import tempfile
from unittest.mock import patch
import performance
with tempfile.TemporaryDirectory() as root:
    engine = performance.Engine(root, "actual-user")
    engine.import_history([{"notes": "x" * 140000}])
    valid = engine.path.read_bytes()
    csv.field_size_limit(512)
    cases = {
        "startup": OSError("child unavailable"),
        "exit": subprocess.CompletedProcess([], 1, b"", b"child rejected CSV"),
        "json": subprocess.CompletedProcess([], 0, b"not JSON", b""),
        "utf8_output": subprocess.CompletedProcess([], 0, b"\xff", b""),
        "shape": subprocess.CompletedProcess([], 0, b'{"unexpected":true}', b""),
        "row_shape": subprocess.CompletedProcess([], 0, b'[["data"],[{"data":{"unexpected":true}}]]', b""),
    }
    report = {}
    opened = os.open
    for name, outcome in cases.items():
        descriptors = []
        def capture_open(path, *args, **kwargs):
            descriptor = opened(path, *args, **kwargs)
            if str(path) == engine.path.name or str(path) == str(engine.path):
                descriptors.append(descriptor)
            return descriptor
        def fail(*args, **kwargs):
            assert kwargs["shell"] is False
            assert kwargs["close_fds"] is True
            assert kwargs["stdin"].fileno() in descriptors
            if isinstance(outcome, BaseException):
                raise outcome
            from unittest.mock import MagicMock
            process = MagicMock()
            process.__enter__.return_value = process
            process.communicate.return_value = (outcome.stdout, outcome.stderr)
            process.returncode = outcome.returncode
            return process
        error = None
        with patch("subprocess.Popen", side_effect=fail) as run, patch("performance.os.open", side_effect=capture_open):
            try:
                engine.status("session-a")
            except Exception as caught:
                error = type(caught).__name__
        closed = True
        for descriptor in descriptors:
            try:
                os.fstat(descriptor)
                closed = False
            except OSError:
                pass
        report[name] = {"error": error, "calls": run.call_count, "closed": closed,
                        "unchanged": engine.path.read_bytes() == valid}
    for name, bad in {"utf8_input": b"\xff", "malformed_csv": b'"unterminated'}.items():
        engine.path.write_bytes(valid.split(b"\r\n", 1)[0] + b"\r\n" + bad)
        before = engine.path.read_bytes()
        try:
            engine.status("session-a")
            error = None
        except Exception as caught:
            error = type(caught).__name__
        report[name] = {"error": error, "unchanged": engine.path.read_bytes() == before}
    print(json.dumps(report))
"""
        result = subprocess.run([sys.executable, "-c", program], cwd=str(SCRIPT.parent),
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        for case in ("startup", "exit", "json", "utf8_output", "shape", "row_shape"):
            with self.subTest(case=case):
                self.assertEqual(report[case]["error"], "OSError" if case == "startup" else "ValueError")
                self.assertEqual(report[case]["calls"], 1)
                self.assertTrue(report[case]["closed"])
                self.assertTrue(report[case]["unchanged"])
        self.assertEqual(report["utf8_input"]["error"], "UnicodeDecodeError")
        self.assertEqual(report["malformed_csv"]["error"], "ValueError")
        self.assertTrue(report["utf8_input"]["unchanged"])
        self.assertTrue(report["malformed_csv"]["unchanged"])

    @unittest.skipUnless(__import__("os").name == "posix", "requires POSIX interrupt and ledger rename")
    def test_isolated_csv_reader_anchors_stdin_and_reaps_cancelled_child(self):
        program = r"""
import csv
import json
import os
import signal
import subprocess
import tempfile
import threading
from unittest.mock import patch
import performance
with tempfile.TemporaryDirectory() as root:
    engine = performance.Engine(root, "actual-user")
    engine.import_history([{"notes": "x" * 140000}])
    valid = engine.path.read_bytes()
    csv.field_size_limit(512)
    real_popen = subprocess.Popen
    captured = []
    retained = engine.path.with_name("retained.csv")
    def move_after_spawn(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        captured.append(process)
        engine.path.rename(retained)
        engine.path.write_bytes(b"replacement untouched")
        return process
    with patch("subprocess.Popen", side_effect=move_after_spawn):
        anchored = engine.status("session-a")
    assert retained.read_bytes() == valid
    assert engine.path.read_bytes() == b"replacement untouched"
    assert captured[0].poll() == 0
    engine.path.unlink()
    retained.rename(engine.path)
    captured = []
    timers = []
    def interrupt_after_spawn(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        captured.append(process)
        timer = threading.Timer(0.05, lambda: os.kill(os.getpid(), signal.SIGINT))
        timers.append(timer)
        timer.start()
        return process
    cancelled = False
    with patch("performance._CSV_READER_CODE", "import time; time.sleep(60)", create=True), patch(
            "subprocess.Popen", side_effect=interrupt_after_spawn):
        try:
            engine.status("session-a")
        except KeyboardInterrupt:
            cancelled = True
    for timer in timers:
        timer.join()
    print(json.dumps({"anchored": not anchored["enabled"], "cancelled": cancelled,
                      "reaped": bool(captured) and captured[0].poll() is not None,
                      "unchanged": engine.path.read_bytes() == valid,
                      "pending": len(list(engine.directory.glob(".pending-*"))),
                      "limit": csv.field_size_limit()}))
"""
        result = subprocess.run([sys.executable, "-c", program], cwd=str(SCRIPT.parent),
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["anchored"])
        self.assertTrue(report["cancelled"])
        self.assertTrue(report["reaped"])
        self.assertTrue(report["unchanged"])
        self.assertEqual(report["pending"], 0)
        self.assertEqual(report["limit"], 512)

    def test_import_preserves_unrelated_csv_reader_limit(self):
        program = """
import csv
import json
csv.field_size_limit(512)
import performance
print(json.dumps({"limit": csv.field_size_limit()}))
"""
        result = subprocess.run([sys.executable, "-c", program], cwd=str(SCRIPT.parent),
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["limit"], 512)

    def test_large_history_read_preserves_concurrent_unrelated_reader_policy(self):
        program = """
import csv
import io
import json
import tempfile
import threading
import time
import performance
with tempfile.TemporaryDirectory() as root:
    engine = performance.Engine(root, "actual-user")
    imported = [{"notes": "x" * 140000}]
    engine.import_history(imported)
    before = engine.path.read_bytes()
    csv.field_size_limit(512)
    ready, stop = threading.Event(), threading.Event()
    counts = {"rejected": 0, "accepted": 0}
    def unrelated_reader():
        while not stop.is_set():
            try:
                next(csv.reader(io.StringIO("x" * 513)))
                counts["accepted"] += 1
            except csv.Error:
                counts["rejected"] += 1
            ready.set()
            time.sleep(0.001)
    thread = threading.Thread(target=unrelated_reader)
    thread.start()
    error = None
    try:
        assert ready.wait(5), "unrelated reader did not start"
        engine.status("session-a")
        assert engine._load()[-1]["data"]["rows"] == imported
        assert engine.import_history(imported)["duplicate"]
    except Exception as caught:
        error = type(caught).__name__ + ": " + str(caught)
    finally:
        stop.set()
        thread.join()
    print(json.dumps({"error": error, "limit": csv.field_size_limit(), "counts": counts,
                      "unchanged": engine.path.read_bytes() == before}))
"""
        result = subprocess.run([sys.executable, "-c", program], cwd=str(SCRIPT.parent),
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertIsNone(report["error"])
        self.assertEqual(report["limit"], 512)
        self.assertGreater(report["counts"]["rejected"], 0)
        self.assertEqual(report["counts"]["accepted"], 0)
        self.assertTrue(report["unchanged"])

    def test_commit_rejects_fields_beyond_private_codec_character_limit_without_publication(self):
        program = r"""
import copy
import csv
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import performance
limit = 512
csv.field_size_limit(limit)  # Isolated subprocess; never lower the test runner's shared setting.

def imported_at_size(size):
    rows = [{"notes": 'λ,"quoted"\n'}]
    def serialized():
        _, digest = performance._legacy_payload(rows)
        return performance._json({"rows": rows, "digest": digest})
    rows[0]["notes"] += "a" * (size - len(serialized()))
    assert len(serialized()) == size
    return rows, serialized()

with tempfile.TemporaryDirectory() as root:
    engine = performance.Engine(root, "actual-user")
    engine.set_enabled("session-a", True)
    boundary, data = imported_at_size(limit)
    wire = io.StringIO(newline="")
    csv.writer(wire).writerow([data])
    assert len(wire.getvalue().rstrip("\r\n")) > limit, "fixture must exercise CSV quote expansion"
    with patch("performance._CSV_FIELD_LIMIT", limit):
        engine.import_history(boundary)
        assert engine._load()[-1]["data"]["rows"] == boundary
        before = engine.path.read_bytes()
        assert engine.import_history(boundary)["duplicate"]
        assert engine.path.read_bytes() == before
        oversized, _ = imported_at_size(limit + 1)
        error = None
        try:
            engine.import_history(oversized)
        except ValueError as caught:
            error = str(caught)
        report = {"oversized_error": error, "oversized_unchanged": engine.path.read_bytes() == before}
        engine.path.write_bytes(before)  # Restore only this disposable fixture if the regression is present.
        valid = engine._load()
        unicode_rows = copy.deepcopy(valid)
        unicode_rows[-1]["run_id"] = "λ" * limit
        with engine._locked() as access:
            engine._load(access)
            engine._commit(unicode_rows, access)
        with engine.path.open(newline="", encoding="utf-8") as stream:
            decoded = list(csv.DictReader(stream))
        report["unicode_character_boundary"] = decoded[-1]["run_id"] == "λ" * limit
        engine.path.write_bytes(before)  # This low-level CSV fixture intentionally bypasses projection semantics.
        fields = {}
        for field in performance.FIELDS:
            rows = copy.deepcopy(valid)
            if field == "data":
                rows[-1][field]["extra"] = "x" * (limit + 1)
            else:
                rows[-1][field] = "λ" * (limit + 1)
            error = None
            try:
                with engine._locked() as access:
                    engine._load(access)
                    engine._commit(rows, access)
            except ValueError as caught:
                error = str(caught)
            fields[field] = {"error": error, "unchanged": engine.path.read_bytes() == before,
                             "pending": len(list(engine.directory.glob(".pending-*")))}
            engine.path.write_bytes(before)
        report["fields"] = fields
        report["boundary_readable"] = engine._load()[-1]["data"]["rows"] == boundary
print(json.dumps(report))
"""
        result = subprocess.run([sys.executable, "-c", program], cwd=str(SCRIPT.parent),
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertIsNotNone(report["oversized_error"], "oversized import was acknowledged")
        self.assertIn("field", report["oversized_error"])
        self.assertIn("512", report["oversized_error"])
        self.assertTrue(report["oversized_unchanged"])
        self.assertTrue(report["boundary_readable"])
        self.assertTrue(report["unicode_character_boundary"])
        for field, outcome in report["fields"].items():
            with self.subTest(field=field):
                self.assertIsNotNone(outcome["error"], "oversized event field was published")
                self.assertIn(field, outcome["error"])
                self.assertTrue(outcome["unchanged"])
                self.assertEqual(outcome["pending"], 0)

    def test_large_legacy_import_remains_readable_lossless_and_idempotent_after_restart(self):
        import performance
        notes = ('λ,"quoted"\\n' * 14000) + "tail"
        imported = [{"notes": notes, "nested": {"items": [None, True, 4]}}]
        self.assertGreater(len(performance._json(imported)), 128 * 1024)
        result = self.engine.import_history(imported)
        self.assertEqual(result["imported_count"], 1)
        self.assertFalse(result["eligible"])
        published = self.engine.path.read_bytes()
        restarted = Engine(self.root, "actual-user")
        with patch("performance.csv.field_size_limit", side_effect=AssertionError("reads must not reconfigure global CSV limits")):
            self.assertFalse(restarted.status(self.session)["enabled"])
            loaded = restarted._load()
            self.assertEqual(loaded[-1]["data"]["rows"], imported)
            self.assertTrue(restarted.import_history(imported)["duplicate"])
        self.assertEqual(restarted.path.read_bytes(), published)
        status = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root),
                                 "--user", "actual-user", "--session", self.session, "status"],
                                text=True, capture_output=True)
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertFalse(json.loads(status.stdout)["enabled"])
        self.assertEqual(restarted.path.read_bytes(), published)

    def test_private_csv_codec_ceiling_preserves_parent_policy_on_c_long_platform(self):
        program = """
import csv
import json
import subprocess
import sys
from unittest.mock import patch
csv.field_size_limit(512)
with patch("csv.field_size_limit", side_effect=AssertionError("parent parser policy touched")), patch(
        "ctypes.sizeof", return_value=4):
    import performance
assert performance._CSV_FIELD_LIMIT == (1 << 31) - 1
payload = "data\\n" + "x" * 140000 + "\\n"
result = subprocess.run([sys.executable, "-I", "-c", performance._CSV_READER_CODE,
                         str(performance._CSV_FIELD_LIMIT)], input=payload.encode("utf-8"),
                        capture_output=True)
assert result.returncode == 0, result.stderr
assert json.loads(result.stdout)[1][0]["data"] == "x" * 140000
print(json.dumps({"limit": csv.field_size_limit(), "ceiling": performance._CSV_FIELD_LIMIT}))
"""
        result = subprocess.run([sys.executable, "-c", program], cwd=str(SCRIPT.parent),
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads(result.stdout)
        self.assertEqual(state["limit"], 512)
        self.assertEqual(state["ceiling"], (1 << 31) - 1)

    @unittest.skipUnless(__import__("os").name == "posix", "requires POSIX directory movement while pinned")
    def test_postpublication_identity_check_rejects_moves_inside_link_and_replace(self):
        import os
        for first_publication in (True, False):
            for move_root in (True, False):
                with self.subTest(first_publication=first_publication, move_root=move_root), tempfile.TemporaryDirectory() as base:
                    root = Path(base) / "project"
                    root.mkdir()
                    engine = Engine(root, "actual-user")
                    if not first_publication:
                        engine.set_enabled(self.session, True)
                    before = engine.path.read_bytes() if engine.path.exists() else b""
                    retained = Path(base) / "retained"
                    sentinel = b"replacement ledger must remain untouched"
                    primitive = os.link if first_publication else os.replace
                    moved = False

                    def publish(*args, **kwargs):
                        nonlocal moved
                        if move_root:
                            root.rename(retained)
                            engine.directory.mkdir(parents=True)
                        else:
                            engine.directory.rename(retained)
                            engine.directory.mkdir()
                        engine.path.write_bytes(sentinel)
                        moved = True
                        return primitive(*args, **kwargs)

                    error = None
                    with patch("performance.os.link" if first_publication else "performance.os.replace",
                               side_effect=publish):
                        try:
                            if first_publication:
                                engine.set_enabled(self.session, True)
                            else:
                                engine.prepare(self.session, "codex", "executor", "low", MODELS, list(range(7)))
                        except (ValueError, OSError) as caught:
                            error = caught
                    self.assertTrue(moved)
                    retained_directory = retained / "model-perf" if move_root else retained
                    retained_ledger = retained_directory / engine.path.name
                    published = retained_ledger.read_bytes()
                    self.assertTrue(published.startswith(before))
                    self.assertNotEqual(published, before)
                    with retained_ledger.open(newline="", encoding="utf-8") as stream:
                        rows = list(csv.DictReader(stream))
                    self.assertEqual(rows[-1]["event_type"], "session" if first_publication else "launch")
                    self.assertTrue(all(None not in row and None not in row.values() for row in rows))
                    self.assertEqual(engine.path.read_bytes(), sentinel)
                    self.assertEqual(list(engine.directory.iterdir()), [engine.path])
                    self.assertEqual(list(retained_directory.iterdir()), [retained_ledger])
                    self.assertIsInstance(error, ValueError, "postpublication movement falsely acknowledged success")
                    self.assertRegex(str(error), "project root|ledger directory")

    @unittest.skipUnless(__import__("os").name == "posix", "requires POSIX directory movement while pinned")
    def test_postpublication_identity_check_rejects_relocation_directory_move(self):
        import os
        old = self.root.resolve() / "old-project"
        old.mkdir()
        engine = Engine(old, "actual-user")
        engine.set_enabled(self.session, True)
        before = engine.path.read_bytes()
        new = self.root.resolve() / "new-project"
        old.rename(new)
        moved = Engine(new, "actual-user")
        retained = self.root / "retained-model-perf"
        sentinel = b"replacement relocation ledger"
        replace = os.replace

        def publish(*args, **kwargs):
            moved.directory.rename(retained)
            moved.directory.mkdir()
            moved.path.write_bytes(sentinel)
            return replace(*args, **kwargs)

        error = None
        with patch("performance.os.replace", side_effect=publish):
            try:
                moved.relocate(str(old))
            except (ValueError, OSError) as caught:
                error = caught
        retained_ledger = retained / moved.path.name
        self.assertTrue(retained_ledger.read_bytes().startswith(before))
        with retained_ledger.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(rows[-1]["event_type"], "relocation")
        self.assertEqual(json.loads(rows[-1]["data"]), {"from_root": str(old), "to_root": str(new)})
        self.assertEqual(moved.path.read_bytes(), sentinel)
        self.assertEqual(list(moved.directory.iterdir()), [moved.path])
        self.assertEqual(list(retained.iterdir()), [retained_ledger])
        self.assertIsInstance(error, ValueError, "relocation falsely acknowledged changed directory")
        self.assertRegex(str(error), "ledger directory")

    @unittest.skipUnless(__import__("os").name == "posix", "requires POSIX directory movement while pinned")
    def test_postpublication_identity_check_confirms_noop_and_already_synced_mutations(self):
        import os
        for already_confirmed in (False, True):
            with self.subTest(already_confirmed=already_confirmed), tempfile.TemporaryDirectory() as base:
                engine = Engine(base, "actual-user")
                engine.set_enabled(self.session, True)
                retained = Path(base) / "retained-model-perf"
                sentinel = b"replacement after sync"
                fsync, status = os.fsync, engine._status

                def move():
                    engine.directory.rename(retained)
                    engine.directory.mkdir()
                    engine.path.write_bytes(sentinel)

                def sync_then_move(descriptor):
                    result = fsync(descriptor)
                    if os.path.samestat(os.fstat(descriptor), engine.directory.stat()):
                        move()
                    return result

                def result_then_move(*args, **kwargs):
                    result = status(*args, **kwargs)
                    move()
                    return result

                error = None
                target = patch.object(engine, "_status", side_effect=result_then_move) if already_confirmed else patch(
                    "performance.os.fsync", side_effect=sync_then_move)
                with target:
                    try:
                        engine.set_enabled(self.session, not already_confirmed)
                    except (ValueError, OSError) as caught:
                        error = caught
                retained_ledger = retained / engine.path.name
                with retained_ledger.open(newline="", encoding="utf-8") as stream:
                    rows = list(csv.DictReader(stream))
                self.assertEqual(json.loads(rows[-1]["data"])["enabled"], not already_confirmed)
                self.assertEqual(engine.path.read_bytes(), sentinel)
                self.assertEqual(list(engine.directory.iterdir()), [engine.path])
                self.assertEqual(list(retained.iterdir()), [retained_ledger])
                self.assertIsInstance(error, ValueError, "mutation success missed a final identity change")
                self.assertRegex(str(error), "ledger directory")

    def test_v4_adoption_preserves_unchanged_windows_and_retires_only_claude_advisor(self):
        write_policy_two_fixture(self.engine, self.session)
        rows = self.events()
        self.engine._append(rows, "policy_adoption", {"from_policy_version": "optimal-ultra-ladder-v2", "to_policy_version": "optimal-ultra-ladder-v3"})
        old_runs = {}
        for platform, family, effort, models in (("codex", "sol", "xhigh", {"sol": "sol-old", "astra": "astra-old"}),
                                                  ("claude", "opus", "medium", {"opus": "opus-old"})):
            track = dict(platform=platform, role="advisor", tier=None, step=0, family=family,
                         effort=effort, model_id=models[family], epoch=platform + "-v3-epoch",
                         models=models, available_steps=[0, 1, 2], reason="initial", previous_epoch=None,
                         policy_version="optimal-ultra-ladder-v3", advice_level="medium", context_floor=0)
            self.engine._append(rows, "transition", track)
            for i in range(2):
                run = dict(track, run_id=f"{platform}-v3-{i}", session=self.session,
                           user_id=self.engine.user, session_generation="legacy-generation", mode="direct")
                self.engine._append(rows, "launch", run)
                if i == 0:
                    request = dict(run_id=run["run_id"], score=4, effective_model_id=run["model_id"],
                                   effective_effort=effort, execution_id=platform + "-v3-exec", verified=True)
                    attribution = {key: run[key] for key in ("platform", "role", "tier", "step", "model_id", "epoch", "run_id", "policy_version")}
                    attribution.update(score=4, verified=True, timestamp="2026-11-07T00:04:00+00:00")
                    self.engine._append(rows, "assessment", dict(request=request, attribution=attribution,
                        result=dict(run_id=run["run_id"], eligible=True, exclusions=[], transition=None)))
                old_runs[platform] = run
        self.write_events(rows)
        self.assertEqual(self.engine.status(self.session)["policy_version"], "optimal-ultra-ladder-v3")
        corrupt = self.events()
        transition = next(row for row in corrupt if row["event_type"] == "transition" and row["platform"] == "claude")
        transition["data"]["context_floor"] = 1
        self.write_events(corrupt)
        with self.assertRaisesRegex(ValueError, "context floor"):
            self.engine.status(self.session)
        self.write_events(rows)
        corrupt = self.events()
        adoption = next(row for row in corrupt if row["event_type"] == "policy_adoption")
        adoption["data"]["to_policy_version"] = "optimal-ultra-ladder-v4"
        self.write_events(corrupt)
        with self.assertRaisesRegex(ValueError, "policy adoption"):
            self.engine.status(self.session)
        self.write_events(rows)
        legacy_fields = [field for field in rows[0] if field != "tier"]
        with self.engine.path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=legacy_fields)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: ("1" if field == "schema_version" else
                                         json.dumps(row[field]) if field == "data" else row[field])
                                 for field in legacy_fields})
        self.assertEqual(self.engine.status(self.session)["policy_version"], "optimal-ultra-ladder-v3")
        before = self.engine.path.read_bytes()
        with patch("performance.os.replace", side_effect=PermissionError("adoption denied")):
            with self.assertRaises(PermissionError):
                self.engine.adopt_policy()
        self.assertEqual(self.engine.path.read_bytes(), before)
        self.assertTrue(self.engine.adopt_policy()["changed"])
        upgraded = self.events()
        self.assertEqual({event["schema_version"] for event in upgraded}, {"2"})
        for old, current in zip(rows, upgraded):
            self.assertEqual({key: value for key, value in old.items() if key != "schema_version"},
                             {key: value for key, value in current.items() if key != "schema_version"})
        self.assertFalse(self.engine.adopt_policy()["changed"])
        status = Engine(self.root, "actual-user").status(self.session)
        self.assertEqual(status["policy_version"], "optimal-ultra-ladder-v4")
        tracks = {(t["platform"], t["role"]): t for t in status["tracks"]}
        self.assertEqual((tracks[("codex", "executor")]["epoch"], tracks[("codex", "executor")]["eligible_count"]), ("executor-v1", 3))
        self.assertEqual((tracks[("codex", "advisor")]["epoch"], tracks[("codex", "advisor")]["eligible_count"]), ("codex-v3-epoch", 1))
        self.assertNotIn(("claude", "advisor"), tracks)
        self.assertTrue(self.assess(old_runs["codex"])["eligible"])
        self.assertIn("policy_changed", self.assess(old_runs["claude"])["exclusions"])
        fresh = self.engine.prepare(self.session, "claude", "advisor", models={"opus": "opus-old"},
                                    available_steps=[0, 1, 2, 3], advice_level="super_high")
        self.assertEqual((fresh["step"], fresh["context_floor"]), (2, 2))
        self.assertNotEqual(fresh["epoch"], "claude-v3-epoch")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.engine = Engine(self.root, "actual-user")
        self.session = "session-a"

    def enable(self):
        return self.engine.set_enabled(self.session, True)

    def prepare(self, **overrides):
        arguments = dict(session=self.session, platform="codex", role="executor",
                         tier="low", models=MODELS, available_steps=list(range(7)))
        arguments.update(overrides)
        return self.engine.prepare(**arguments)

    def assess(self, run, score=4, **overrides):
        arguments = dict(run_id=run["run_id"], score=score,
                         effective_model_id=run["model_id"], effective_effort=run["effort"],
                         execution_id="exec-" + run["run_id"], verified=True)
        arguments.update(overrides)
        return self.engine.assess(**arguments)

    def events(self):
        with self.engine.path.open(newline="", encoding="utf-8") as stream:
            return [dict(row, data=json.loads(row["data"])) for row in csv.DictReader(stream)]

    def test_explicit_relocation_preserves_history_and_rejects_wrong_origin(self):
        old = self.root.resolve() / 'old-project'
        old.mkdir()
        original = Engine(old, 'actual-user')
        original.set_enabled('existing-session', True)
        with original.path.open(newline='', encoding='utf-8') as stream:
            before = list(csv.DictReader(stream))
        new = self.root.resolve() / 'new-project'
        old.rename(new)
        moved = Engine(new, 'actual-user')
        with self.assertRaisesRegex(ValueError, 'binding mismatch'):
            moved.status('existing-session')
        self.assertTrue(hasattr(moved, 'relocate'), 'explicit relocation is unavailable')
        with self.assertRaises(ValueError):
            moved.relocate(str(self.root / 'wrong-project'))
        with moved.path.open(newline='', encoding='utf-8') as stream:
            self.assertEqual(list(csv.DictReader(stream)), before)
        moved.relocate(str(old))
        self.assertTrue(Engine(new, 'actual-user').status('existing-session')['enabled'])
        with moved.path.open(newline='', encoding='utf-8') as stream:
            after = list(csv.DictReader(stream))
        self.assertEqual(after[:-1], before)
        self.assertEqual(after[-1]['event_type'], 'relocation')
        self.assertEqual(json.loads(after[-1]['data']), {'from_root': str(old), 'to_root': str(new)})

        newest = self.root.resolve() / 'newest-project'
        new.rename(newest)
        twice_moved = Engine(newest, 'actual-user')
        twice_moved.relocate(str(new))
        self.assertTrue(twice_moved.status('existing-session')['enabled'])
        with twice_moved.path.open(newline='', encoding='utf-8') as stream:
            rows = list(csv.DictReader(stream))
        rows[-1]['data'] = json.dumps({'from_root': str(old), 'to_root': str(newest)})
        with twice_moved.path.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaisesRegex(ValueError, 'invalid ledger relocation'):
            twice_moved.status('existing-session')

    def test_relocation_preserves_assessments_epoch_and_window_across_restart(self):
        old = self.root.resolve() / 'history-old'
        old.mkdir()
        self.engine = Engine(old, 'actual-user')
        self.enable()
        runs = [self.prepare() for _ in range(5)]
        outcomes = [self.assess(run) for run in runs[:4]]
        before_track = self.engine.status(self.session)['tracks'][0]
        self.assertEqual(before_track['eligible_count'], 4)
        self.assertEqual(before_track['epoch'], runs[0]['epoch'])
        new = self.root / 'history-new'
        old.rename(new)
        self.engine = Engine(new, 'actual-user')
        self.engine.relocate(str(old))

        self.engine = Engine(new, 'actual-user')
        self.assertEqual(self.engine.status(self.session)['tracks'][0], before_track)
        before_retry = self.engine.path.read_bytes()
        self.assertEqual(self.assess(runs[0]), outcomes[0])
        self.assertEqual(self.engine.path.read_bytes(), before_retry)
        result = self.assess(runs[4])
        self.assertEqual(result['transition']['step'], 1)
        track = Engine(new, 'actual-user').status(self.session)['tracks'][0]
        self.assertEqual(track['step'], 1)
        self.assertNotEqual(track['epoch'], before_track['epoch'])
        self.assertEqual(self.prepare()['epoch'], track['epoch'])

    def test_failed_relocation_replace_preserves_history_and_cleans_temporary(self):
        old = self.root.resolve() / 'atomic-old'
        old.mkdir()
        self.engine = Engine(old, 'actual-user')
        self.enable()
        self.assess(self.prepare())
        new = self.root / 'atomic-new'
        old.rename(new)
        self.engine = Engine(new, 'actual-user')
        before = self.engine.path.read_bytes()
        with patch('performance.os.replace', side_effect=PermissionError('write denied')):
            with self.assertRaises(PermissionError):
                self.engine.relocate(str(old))
        self.assertEqual(self.engine.path.read_bytes(), before)
        self.assertEqual([path.name for path in self.engine.directory.iterdir()],
                         ['actual-user-model-perf.csv'])
        self.engine.relocate(str(old))
        self.assertEqual(Engine(new, 'actual-user').status(self.session)['tracks'][0]['eligible_count'], 1)

    @unittest.skipUnless(__import__("os").name == "posix", "requires POSIX directory fsync")
    def test_relocation_postpublication_sync_error_recovery_preserves_binding_and_history(self):
        import os
        old = self.root.resolve() / "relocation-sync-old"
        old.mkdir()
        original = Engine(old, "actual-user")
        original.set_enabled(self.session, True)
        before = original.path.read_bytes()
        original_policy = original.status(self.session)["policy_version"]
        new = self.root.resolve() / "relocation-sync-new"
        old.rename(new)
        moved = Engine(new, "actual-user")
        fsync = os.fsync
        child_syncs = []

        def fail_child_sync(descriptor):
            if os.path.samestat(os.fstat(descriptor), moved.directory.stat()):
                child_syncs.append(descriptor)
                raise OSError("relocation namespace unconfirmed")
            return fsync(descriptor)

        with patch("performance.os.fsync", side_effect=fail_child_sync):
            with self.assertRaisesRegex(OSError, "relocation namespace unconfirmed"):
                moved.relocate(str(old))
        visible = moved.path.read_bytes()
        self.assertTrue(visible.startswith(before), "relocation rewrote historical bytes")
        with moved.path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        relocations = [row for row in rows if row["event_type"] == "relocation"]
        self.assertEqual(len(relocations), 1)
        self.assertEqual(json.loads(relocations[0]["data"]),
                         {"from_root": str(old), "to_root": str(new)})
        self.assertEqual(list(moved.directory.iterdir()), [moved.path])
        with patch("performance.os.fsync", side_effect=fail_child_sync):
            status = Engine(new, "actual-user").status(self.session)
            self.assertTrue(status["enabled"])
            self.assertEqual(status["policy_version"], original_policy)
            self.assertEqual(len(child_syncs), 1, "status must not confirm durability")
            with self.assertRaisesRegex(ValueError, "binding mismatch"):
                moved.relocate(str(old))
            self.assertEqual(len(child_syncs), 1, "wrong-origin retry must fail before mutation")
            self.assertEqual(moved.path.read_bytes(), visible)
            with self.assertRaisesRegex(OSError, "relocation namespace unconfirmed"):
                moved.adopt_policy()
        self.assertEqual(len(child_syncs), 2)
        self.assertEqual(moved.path.read_bytes(), visible)
        recovered_syncs = []

        def recover_sync(descriptor):
            self.assertTrue(os.path.samestat(os.fstat(descriptor), moved.directory.stat()))
            self.assertEqual(moved.path.read_bytes(), visible)
            recovered_syncs.append(descriptor)
            return fsync(descriptor)

        with patch("performance.os.fsync", side_effect=recover_sync), patch(
                "performance.os.replace") as replace, patch("performance.os.link") as link:
            result = moved.adopt_policy()
        self.assertEqual(result, {"changed": False, "policy_version": original_policy})
        self.assertEqual(len(recovered_syncs), 1)
        replace.assert_not_called()
        link.assert_not_called()
        self.assertEqual(moved.path.read_bytes(), visible)

    def test_relocation_cli_uses_explicit_request(self):
        old = self.root.resolve() / 'cli-old'
        old.mkdir()
        Engine(old, 'actual-user').set_enabled('session-a', True)
        new = self.root.resolve() / 'cli-new'
        old.rename(new)
        request = self.root / 'request.json'
        request.write_text(json.dumps({'from_root': str(old)}), encoding='utf-8')
        result = subprocess.run([sys.executable, str(SCRIPT), '--root', str(new),
                                 '--user', 'actual-user', '--session', 'session-a',
                                 'relocate', str(request)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['to_root'], str(new))
        self.assertTrue(Engine(new, 'actual-user').status('session-a')['enabled'])

    def test_default_off_read_only_and_explicit_session_enable(self):
        self.assertFalse(self.engine.status(self.session)["enabled"])
        self.assertFalse(self.engine.path.exists())
        with self.assertRaisesRegex(ValueError, "disabled"):
            self.prepare()
        self.enable()
        self.assertTrue(Engine(self.root, "actual-user").status(self.session)["enabled"])
        self.assertFalse(self.engine.status("other-session")["enabled"])


    def test_disabled_contract_defers_to_host_policy_without_blanket_root_permission(self):
        result = self.engine.status(self.session)
        self.assertEqual(result.get("execution_contract", {}).get("root_execution"), "governing_host_policy")
        self.assertIs(result.get("execution_contract", {}).get("blanket_root_permission"), False)
        self.assertFalse(self.engine.path.exists())

    def test_mode_contract_survives_status_without_new_events_or_learning(self):
        enabled = self.enable()
        self.assertEqual(enabled.get("execution_contract", {}).get("substantive_owner"), "executor")
        self.assertIs(enabled.get("execution_contract", {}).get("advisor_authorizes_execution"), False)
        before = self.engine.path.read_bytes()
        status = Engine(self.root, "actual-user").status(self.session)
        self.assertEqual(status.get("execution_contract"), enabled.get("execution_contract"))
        self.assertEqual(self.engine.path.read_bytes(), before)
        self.assertEqual(status["tracks"], [])
        off = self.engine.set_enabled(self.session, False)
        self.assertEqual(off.get("execution_contract", {}).get("root_execution"), "governing_host_policy")
        self.assertIs(off.get("execution_contract", {}).get("blanket_root_permission"), False)

    def test_replay_rejects_reused_or_redundant_session_events(self):
        self.enable()
        pending = self.prepare()
        self.engine.set_enabled(self.session, False)
        self.enable()
        original = self.engine.path.read_bytes()
        for case in ("reused_generation", "redundant_event"):
            for operation in ("status", "assess"):
                with self.subTest(case=case, operation=operation):
                    self.engine.path.write_bytes(original)
                    rows = self.events()
                    sessions = [row for row in rows if row["event_type"] == "session"]
                    if case == "reused_generation":
                        sessions[-1]["data"]["generation"] = sessions[0]["data"]["generation"]
                    else:
                        self.engine._append(rows, "session",
                                            dict(session=self.session, enabled=True, generation="fresh-generation"))
                    self.write_events(rows)
                    corrupted = self.engine.path.read_bytes()
                    with self.assertRaises(ValueError):
                        if operation == "status":
                            self.engine.status(self.session)
                        else:
                            self.assess(pending)
                    self.assertEqual(self.engine.path.read_bytes(), corrupted)

    def test_launch_reserves_exact_settings_and_one_csv_only(self):
        self.enable()
        run = self.prepare()
        self.assertEqual((run["step"], run["family"], run["model_id"], run["effort"]),
                         (0, "terra", "terra-v1", "low"))
        self.assertTrue(run["run_id"])
        self.assertTrue(run["epoch"])
        self.assertEqual(run["mode"], "direct")
        files = sorted(path.name for path in (self.root / "model-perf").iterdir())
        self.assertEqual(files, ["actual-user-model-perf.csv"])
        events = self.events()
        self.assertEqual([int(event["sequence"]) for event in events],
                         list(range(1, len(events) + 1)))
        self.assertEqual({event["user_id"] for event in events}, {"actual-user"})
        self.assertEqual(events[-1]["platform"], "codex")
        self.assertEqual(events[-1]["role"], "executor")
        self.assertEqual(events[-1]["tier"], "low")
        self.assertEqual(events[-1]["schema_version"], "2")
        self.assertEqual(events[-1]["run_id"], run["run_id"])
        self.assertEqual(events[-1]["epoch"], run["epoch"])

    def test_fifth_score_persists_transition_before_restart_or_next_launch(self):
        self.enable()
        runs = [self.prepare() for _ in range(5)]
        for run in runs[:4]:
            self.assess(run)
        self.assertEqual(self.engine.status(self.session)["tracks"][0]["step"], 0)
        result = self.assess(runs[4])
        self.assertEqual(result["transition"]["step"], 1)
        fresh = Engine(self.root, "actual-user")
        track = fresh.status(self.session)["tracks"][0]
        self.assertEqual((track["step"], track["model_id"], track["effort"]), (1, "terra-v1", "medium"))
        self.assertNotEqual(track["epoch"], runs[0]["epoch"])
        launched = fresh.prepare(self.session, "codex", "executor", "low", MODELS, list(range(7)))
        self.assertEqual(launched["epoch"], track["epoch"])

    def test_forged_assessment_transition_is_rejected_on_status_and_retry(self):
        self.enable()
        run = self.prepare()
        self.assertIsNone(self.assess(run, score=5)["transition"])
        rows = self.events()
        rows[-1]["data"]["result"]["transition"] = {"step": 6, "reason": "fabricated"}
        self.write_events(rows)
        corrupted = self.engine.path.read_bytes()
        fresh = Engine(self.root, "actual-user")
        with self.assertRaises(ValueError):
            fresh.status(self.session)
        self.assertEqual(self.engine.path.read_bytes(), corrupted)
        with self.assertRaises(ValueError):
            self.assess(run, score=5)
        self.assertEqual(self.engine.path.read_bytes(), corrupted)

    def test_status_replay_uses_linear_calculator_input_on_long_history(self):
        self.enable()
        run = self.prepare()
        self.assertIsNone(self.assess(run, score=5)["transition"])
        rows = self.events()
        launch = next(row for row in rows if row["event_type"] == "launch")
        assessment = next(row for row in rows if row["event_type"] == "assessment")
        rows = [row for row in rows if row["event_type"] not in ("launch", "assessment")]
        count = 60
        for index in range(count):
            launch_copy = json.loads(json.dumps(launch))
            assessed = json.loads(json.dumps(assessment))
            run_id = f"scale-run-{index}"
            launch_copy["run_id"] = launch_copy["data"]["run_id"] = run_id
            assessed["run_id"] = run_id
            assessed["data"]["request"].update(run_id=run_id, execution_id=f"scale-exec-{index}")
            assessed["data"]["attribution"]["run_id"] = run_id
            assessed["data"]["result"]["run_id"] = run_id
            rows.extend((launch_copy, assessed))
        for sequence, row in enumerate(rows, 1):
            row["sequence"] = str(sequence)
        self.write_events(rows)
        before = self.engine.path.read_bytes()
        visits = []
        def counted(request):
            visits.append(len(request["assessments"]))
            return recommend(request)
        with patch("performance.recommend", side_effect=counted):
            track = Engine(self.root, "actual-user").status(self.session)["tracks"][0]
        self.assertEqual(track["eligible_count"], count)
        self.assertEqual(track["window_run_ids"], [f"scale-run-{i}" for i in range(count - 5, count)])
        self.assertEqual(track["average"], 5)
        self.assertEqual(self.engine.path.read_bytes(), before)
        self.assertLessEqual(sum(visits), 6 * count + 10)

    def test_indexed_replay_matches_full_calculator_with_interleaved_history(self):
        self.enable()
        for index in range(16):
            tier = "low" if index % 2 == 0 else "high"
            models = MODELS if index < 6 else {"terra": "terra-v2", "sol": "sol-v2"}
            run = self.prepare(tier=tier, models=models)
            self.assess(run, score=5, verified=index not in (8, 9))
        rows = self.events()
        assessments = [row for row in rows if row["event_type"] == "assessment"]
        for index, row in enumerate(assessments):
            # Equal timestamps preserve append order; reversed days exercise sorting.
            day = 1 if index in (12, 14) else 28 - index
            row["data"]["attribution"]["timestamp"] = f"2026-01-{day:02d}T00:00:00+00:00"
        self.write_events(rows)
        records = [row["data"]["attribution"] for row in assessments]
        fresh = Engine(self.root, "actual-user")
        tracks = fresh.status(self.session)["tracks"]
        state = fresh._state(fresh._load())
        for track in tracks:
            expected = recommend(dict(track=track, assessments=records,
                                      policy_version=track["policy_version"],
                                      available_steps=track["available_steps"]))
            actual = fresh._recommend(track, state)
            for key in ("eligible_count", "excluded_count", "window_run_ids", "average",
                        "selected_step", "reason", "reset_required"):
                self.assertEqual(actual[key], expected[key], key)
            for key in ("eligible_count", "window_run_ids", "average"):
                self.assertEqual(track[key], expected[key], key)

    def test_invalid_excluded_or_old_assessment_timestamps_are_rejected(self):
        self.enable()
        for index in range(7):
            run = self.prepare()
            self.assess(run, score=5, verified=index != 6)
        original = self.engine.path.read_bytes()
        for index in (0, 6):
            with self.subTest(index=index):
                self.engine.path.write_bytes(original)
                rows = self.events()
                assessments = [row for row in rows if row["event_type"] == "assessment"]
                assessments[index]["data"]["attribution"]["timestamp"] = "invalid"
                self.write_events(rows)
                corrupted = self.engine.path.read_bytes()
                with self.assertRaises(ValueError):
                    Engine(self.root, "actual-user").status(self.session)
                self.assertEqual(self.engine.path.read_bytes(), corrupted)
        self.engine.path.write_bytes(original)

    def test_replay_rejects_corrupt_transition_results_and_events(self):
        self.enable()
        runs = [self.prepare() for _ in range(5)]
        for run in runs:
            result = self.assess(run)
        self.assertEqual(result["transition"]["step"], 1)
        self.engine.set_enabled("another-session", True)
        original = self.engine.path.read_bytes()
        cases = ("none", "missing", "wrong_type", "different", "wrong_step",
                 "wrong_reason", "wrong_model", "missing_event", "moved_event")
        for case in cases:
            with self.subTest(case=case):
                self.engine.path.write_bytes(original)
                rows = self.events()
                assessment = next(row for row in rows if row["event_type"] == "assessment"
                                  and row["data"]["request"]["run_id"] == runs[-1]["run_id"])
                index = rows.index(assessment)
                transition = rows[index + 1]["data"]
                stored = assessment["data"]["result"]
                if case == "none":
                    stored["transition"] = None
                elif case == "missing":
                    del stored["transition"]
                elif case == "wrong_type":
                    stored["transition"] = "invalid"
                elif case == "different":
                    stored["transition"]["reason"] = "fabricated"
                elif case in ("wrong_step", "wrong_reason", "wrong_model"):
                    field, value = {"wrong_step": ("step", 0),
                                    "wrong_reason": ("reason", "fabricated"),
                                    "wrong_model": ("model_id", "fabricated")}[case]
                    stored["transition"][field] = value
                    transition[field] = value
                elif case == "missing_event":
                    del rows[index + 1]
                else:
                    rows[index + 1], rows[index + 2] = rows[index + 2], rows[index + 1]
                for sequence, row in enumerate(rows, 1):
                    row["sequence"] = str(sequence)
                self.write_events(rows)
                corrupted = self.engine.path.read_bytes()
                with self.assertRaises(ValueError):
                    Engine(self.root, "actual-user").status(self.session)
                self.assertEqual(self.engine.path.read_bytes(), corrupted)
                with self.assertRaises(ValueError):
                    self.assess(runs[-1])
                self.assertEqual(self.engine.path.read_bytes(), corrupted)
        self.engine.path.write_bytes(original)

    def test_replay_rejects_boolean_nested_assessment_transition_step(self):
        self.enable()
        runs = [self.prepare() for _ in range(5)]
        for run in runs:
            self.assess(run)
        rows = self.events()
        assessment = next(row for row in rows if row["event_type"] == "assessment"
                          and row["data"]["request"]["run_id"] == runs[-1]["run_id"])
        assessment["data"]["result"]["transition"]["step"] = True
        self.write_events(rows)
        corrupted = self.engine.path.read_bytes()
        with self.assertRaises(ValueError):
            Engine(self.root, "actual-user").status(self.session)
        self.assertEqual(self.engine.path.read_bytes(), corrupted)

    def test_replay_rejects_forged_standalone_transitions_without_mutation(self):
        self.enable()
        first = self.prepare()
        self.prepare(models={"terra": "terra-v2", "sol": "sol-v1"})
        self.prepare(models={"terra": "terra-v3", "sol": "sol-v1"})
        original = self.engine.path.read_bytes()
        for case in ("reason", "predecessor", "impossible_movement", "model_map", "reused_epoch"):
            with self.subTest(case=case):
                self.engine.path.write_bytes(original)
                rows = self.events()
                transitions = [index for index, row in enumerate(rows) if row["event_type"] == "transition"]
                index = transitions[-1]
                rows = rows[:index + 1]
                data = rows[-1]["data"]
                if case == "reason":
                    data["reason"] = "fabricated"
                elif case == "predecessor":
                    data["previous_epoch"] = "fabricated"
                elif case == "impossible_movement":
                    data.update(step=6, family="sol", effort="max", model_id="sol-v1")
                elif case == "model_map":
                    data["model_id"] = "unresolved-model"
                else:
                    data["epoch"] = first["epoch"]
                    rows[-1]["epoch"] = first["epoch"]
                self.write_events(rows)
                corrupted = self.engine.path.read_bytes()
                with self.assertRaises(ValueError):
                    Engine(self.root, "actual-user").status(self.session)
                self.assertEqual(self.engine.path.read_bytes(), corrupted)
                with self.assertRaises(ValueError):
                    self.prepare()
                self.assertEqual(self.engine.path.read_bytes(), corrupted)

    def test_replay_accepts_initial_capability_fallback_to_last_step(self):
        self.enable()
        run = self.prepare(available_steps=[6])
        self.assertEqual(run["step"], 6)
        self.assertEqual(Engine(self.root, "actual-user").status(self.session)["tracks"][0]["step"], 6)

    def test_replay_rejects_boolean_launch_step_without_mutation(self):
        self.enable()
        self.prepare()
        rows = self.events()
        next(row for row in rows if row["event_type"] == "launch")["data"]["step"] = False
        self.write_events(rows)
        corrupted = self.engine.path.read_bytes()
        with self.assertRaises(ValueError):
            Engine(self.root, "actual-user").status(self.session)
        self.assertEqual(self.engine.path.read_bytes(), corrupted)

    def test_replay_rejects_boolean_advisor_context_floor_without_mutation(self):
        self.enable()
        models = {"sol": "sol-v1", "astra": "astra-v1"}
        self.engine.prepare(self.session, "codex", "advisor", models=models,
                            available_steps=[0, 1, 2], advice_level="high")
        self.engine.prepare(self.session, "codex", "advisor", models=models,
                            available_steps=[0, 1, 2], advice_level="medium")
        rows = self.events()
        next(row for row in rows if row["event_type"] == "advisor_context")["data"]["context_floor"] = False
        self.write_events(rows)
        corrupted = self.engine.path.read_bytes()
        with self.assertRaises(ValueError):
            Engine(self.root, "actual-user").status(self.session)
        self.assertEqual(self.engine.path.read_bytes(), corrupted)

    def test_replay_rejects_corrupt_launch_snapshots_before_read_or_mutation(self):
        self.enable()
        self.prepare()
        original = self.engine.path.read_bytes()
        cases = {
            "empty_available": ("available_steps", []),
            "duplicate_available": ("available_steps", [0, 0]),
            "boolean_available": ("available_steps", [0, True]),
            "out_of_range_available": ("available_steps", [0, 7]),
            "current_step_unavailable": ("available_steps", [1, 2]),
            "empty_models": ("models", {}),
            "missing_available_family": ("models", {"terra": "terra-v1"}),
            "nonstring_model": ("models", {"terra": "terra-v1", "sol": 123}),
            "selected_model_mismatch": ("models", {"terra": "different", "sol": "sol-v1"}),
            "invalid_mode": ("mode", "fabricated"),
            "cross_platform_mode": ("mode", "claude-ultracode"),
            "incorrect_reason": ("reason", "fabricated"),
            "incorrect_previous_epoch": ("previous_epoch", "fabricated"),
            "empty_run": ("run_id", ""),
            "empty_session": ("session", ""),
            "empty_user": ("user_id", ""),
            "foreign_user": ("user_id", "different-user"),
            "empty_generation": ("session_generation", ""),
            "stale_generation": ("session_generation", "old-generation"),
            "disabled_session": (None, None),
        }
        for case, (field, value) in cases.items():
            for operation in ("status", "disable"):
                with self.subTest(case=case, operation=operation):
                    self.engine.path.write_bytes(original)
                    rows = self.events()
                    launch = next(row for row in rows if row["event_type"] == "launch")
                    if case == "disabled_session":
                        next(row for row in rows if row["event_type"] == "session")["data"]["enabled"] = False
                    else:
                        launch["data"][field] = value
                        if field == "run_id":
                            launch["run_id"] = value
                    self.write_events(rows)
                    corrupted = self.engine.path.read_bytes()
                    with self.assertRaises(ValueError):
                        if operation == "status":
                            Engine(self.root, "actual-user").status(self.session)
                        else:
                            self.engine.set_enabled(self.session, False)
                    self.assertEqual(self.engine.path.read_bytes(), corrupted)

    def test_replay_accepts_changed_launch_capabilities_at_same_rung(self):
        self.enable()
        first = self.prepare()
        second = self.prepare(models={"terra": "terra-v1", "sol": "sol-v2"},
                              available_steps=[0, 3, 6])
        self.assertEqual(first["epoch"], second["epoch"])
        self.assertEqual(Engine(self.root, "actual-user").status(self.session)["tracks"][0]["available_steps"],
                         [0, 3, 6])

    def test_valid_transition_retries_survive_restart_and_later_advances(self):
        self.enable()
        first_runs = [self.prepare() for _ in range(5)]
        for run in first_runs:
            promotion = self.assess(run, score=4)
        self.assertEqual(promotion["transition"]["step"], 1)
        second_runs = [self.prepare() for _ in range(5)]
        for run in second_runs:
            demotion = self.assess(run, score=5)
        self.assertEqual(demotion["transition"]["step"], 0)
        fresh = Engine(self.root, "actual-user")
        for run, score, result in ((first_runs[-1], 4, promotion), (second_runs[-1], 5, demotion)):
            self.assertEqual(fresh.assess(run["run_id"], score, run["model_id"], run["effort"],
                                          "exec-" + run["run_id"], verified=True), result)
        self.assertEqual(fresh.status(self.session)["tracks"][0]["step"], 0)

    def test_no_transition_can_precede_separate_prepare_rollover(self):
        self.enable()
        run = self.prepare()
        result = self.assess(run, score=5)
        self.assertIsNone(result["transition"])
        self.prepare(models={"terra": "terra-v2", "sol": "sol-v2"})
        fresh = Engine(self.root, "actual-user")
        self.assertEqual(fresh.status(self.session)["tracks"][0]["model_id"], "terra-v2")
        self.assertEqual(fresh.assess(run["run_id"], 5, run["model_id"], run["effort"],
                                      "exec-" + run["run_id"], verified=True), result)

    def test_old_epoch_late_results_never_move_current_or_replay_evidence(self):
        self.enable()
        runs = [self.prepare() for _ in range(11)]
        for run in runs[:5]:
            self.assess(run)
        epoch = self.engine.status(self.session)["tracks"][0]["epoch"]
        for run in runs[5:]:
            outcome = self.assess(run, score=0)
            self.assertIsNone(outcome["transition"])
        self.assertEqual(self.engine.status(self.session)["tracks"][0]["epoch"], epoch)
        self.assertEqual(self.prepare()["step"], 1)

    def test_model_version_change_starts_fresh_epoch(self):
        self.enable()
        first = self.prepare()
        self.assess(first)
        second = self.prepare(models={"terra": "terra-v2", "sol": "sol-v2"})
        self.assertEqual(second["step"], first["step"])
        self.assertNotEqual(second["epoch"], first["epoch"])
        self.assertEqual(second["model_id"], "terra-v2")
        self.assertEqual(self.engine.status(self.session)["tracks"][0]["eligible_count"], 0)

    def test_role_provider_tier_tracks_and_executor_floors_are_separate(self):
        self.enable()
        reservations = [
            self.prepare(),
            self.prepare(tier="medium"),
            self.prepare(tier="high"),
            self.prepare(tier="business_doc"),
            self.prepare(role="advisor", tier=None, available_steps=[0, 1]),
            self.prepare(platform="claude", models=CLAUDE_MODELS, available_steps=list(range(6))),
            self.prepare(platform="claude", role="advisor", tier=None, models=CLAUDE_MODELS, available_steps=[0, 1]),
        ]
        self.assertEqual([run["step"] for run in reservations], [0, 1, 2, 5, 0, 0, 0])
        self.assertEqual(len(self.engine.status(self.session)["tracks"]), 7)
        self.assertEqual(len({run["epoch"] for run in reservations}), 7)

    def test_capability_fallback_transitions_immediately_and_uses_new_family(self):
        self.enable()
        first = self.prepare()
        fallback = self.prepare(available_steps=[3, 6])
        self.assertEqual((fallback["step"], fallback["family"], fallback["model_id"]),
                         (3, "sol", "sol-v1"))
        self.assertNotEqual(first["epoch"], fallback["epoch"])
        with self.assertRaisesRegex(ValueError, "higher"):
            self.prepare(available_steps=[0])

    def test_perfect_results_downshift_only_to_tier_floor(self):
        self.enable()
        self.prepare(available_steps=[1, 2, 3])
        for _ in range(5):
            self.assess(self.prepare(), score=5)
        self.assertEqual(self.engine.status(self.session)["tracks"][0]["step"], 0)
        for _ in range(5):
            self.assess(self.prepare(), score=5)
        self.assertEqual(self.engine.status(self.session)["tracks"][0]["step"], 0)

    def test_unverified_and_substituted_receipts_are_recorded_but_excluded(self):
        self.enable()
        for _ in range(5):
            self.assertFalse(self.assess(self.prepare(), verified=False)["eligible"])
        for _ in range(5):
            self.assertFalse(self.assess(self.prepare(), effective_model_id="other-version")["eligible"])
        for _ in range(5):
            self.assertFalse(self.assess(self.prepare(), effective_effort="high")["eligible"])
        track = self.engine.status(self.session)["tracks"][0]
        self.assertEqual((track["step"], track["eligible_count"]), (0, 0))

    def test_assess_requires_explicit_verified_attestation_before_mutation(self):
        self.enable()
        run = self.prepare()
        request = dict(run_id=run["run_id"], score=4, effective_model_id=run["model_id"],
                       effective_effort=run["effort"], execution_id="reviewed-execution")
        before = self.engine.path.read_bytes()
        with self.assertRaisesRegex(TypeError, "verified"):
            self.engine.assess(**request)
        self.assertEqual(self.engine.path.read_bytes(), before)
        self.assertEqual(self.engine.status(self.session)["tracks"][0]["eligible_count"], 0)
        result = self.engine.assess(**request, verified=True)
        self.assertTrue(result["eligible"])
        self.assertEqual(self.engine.status(self.session)["tracks"][0]["eligible_count"], 1)
        self.assertEqual(self.engine.assess(**request, verified=True), result)

    def test_cli_assess_missing_verified_preserves_ledger_and_allows_corrected_retry(self):
        self.enable()
        run = self.prepare()
        request = dict(run_id=run["run_id"], score=4, effective_model_id=run["model_id"],
                       effective_effort=run["effort"], execution_id="reviewed-cli-execution")
        request_path = self.root / "assessment.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        command = [sys.executable, str(SCRIPT), "--root", str(self.root), "--user",
                   "actual-user", "--session", self.session, "assess", str(request_path)]
        before = self.engine.path.read_bytes()
        rejected = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(rejected.returncode, 1)
        self.assertEqual(rejected.stdout, "")
        self.assertIn("verified", rejected.stderr)
        self.assertNotIn("Traceback", rejected.stderr)
        self.assertEqual(self.engine.path.read_bytes(), before)
        self.assertEqual(self.engine.status(self.session)["tracks"][0]["eligible_count"], 0)
        request["verified"] = True
        request_path.write_text(json.dumps(request), encoding="utf-8")
        accepted = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertTrue(json.loads(accepted.stdout)["eligible"])
        self.assertEqual(self.engine.status(self.session)["tracks"][0]["eligible_count"], 1)

    def test_cached_execution_and_identical_assessment_replay_do_not_count_twice(self):
        self.enable()
        first, second = self.prepare(), self.prepare()
        outcome = self.assess(first, execution_id="provider-cache-key")
        before = self.engine.path.read_bytes()
        self.assertEqual(self.assess(first, execution_id="provider-cache-key"), outcome)
        self.assertEqual(self.engine.path.read_bytes(), before)
        duplicate = self.assess(second, execution_id="provider-cache-key")
        self.assertFalse(duplicate["eligible"])
        self.assertIn("duplicate_execution", duplicate["exclusions"])
        self.assertEqual(self.engine.status(self.session)["tracks"][0]["eligible_count"], 1)
        with self.assertRaisesRegex(ValueError, "already assessed"):
            self.assess(first, score=3, execution_id="provider-cache-key")

    def test_off_blocks_launch_learning_and_reenabled_old_run_remains_excluded(self):
        self.enable()
        before = self.prepare()
        self.engine.set_enabled(self.session, False)
        with self.assertRaisesRegex(ValueError, "disabled"):
            self.prepare()
        disabled_result = self.assess(before)
        self.assertFalse(disabled_result["eligible"])
        self.enable()
        second = self.prepare()
        self.engine.set_enabled(self.session, False)
        self.enable()
        self.assertFalse(self.assess(second)["eligible"])
        self.assertTrue(self.assess(self.prepare())["eligible"])

    def test_users_projects_and_sessions_have_independent_storage_and_enable_state(self):
        self.enable()
        self.prepare()
        other_user = Engine(self.root, "other-user")
        self.assertFalse(other_user.status(self.session)["enabled"])
        self.assertNotEqual(other_user.path, self.engine.path)
        other_root = self.root / "other-project"
        other_root.mkdir()
        self.assertFalse(Engine(other_root, "actual-user").status(self.session)["enabled"])

    def test_unsafe_user_and_symlink_paths_rejected_without_external_writes(self):
        for user in ("", "../escape", "/tmp/user", "a/b", ".", "..", "a\\b", "with space"):
            with self.subTest(user=user), self.assertRaises(ValueError):
                Engine(self.root, user)
        external = self.root / "outside"
        external.mkdir()
        (self.root / "model-perf").symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.enable()
        self.assertEqual(list(external.iterdir()), [])

    def test_ledger_symlink_rejected(self):
        directory = self.root / "model-perf"
        directory.mkdir()
        target = self.root / "target.csv"
        target.write_text("untouched", encoding="utf-8")
        self.engine.path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.enable()
        self.assertEqual(target.read_text(), "untouched")

    def test_ledger_appearing_after_initial_directory_creation_is_not_overwritten(self):
        import os
        sentinel = b'ledger appeared before newly created directory was bound'
        mkdir = os.mkdir
        appeared = False
        def appear_after_mkdir(path, *args, **kwargs):
            nonlocal appeared
            result = mkdir(path, *args, **kwargs)
            if Path(path).name == self.engine.directory.name:
                self.engine.path.write_bytes(sentinel)
                appeared = True
            return result
        error = None
        with patch('performance.os.mkdir', side_effect=appear_after_mkdir):
            try:
                self.engine.set_enabled(self.session, True)
            except (ValueError, OSError) as caught:
                error = caught
        self.assertTrue(appeared, 'ledger appearance after initial mkdir was not exercised')
        self.assertEqual(self.engine.path.read_bytes(), sentinel,
                         'transaction overwrote a ledger that appeared before directory binding')
        self.assertEqual(list(self.engine.directory.iterdir()), [self.engine.path])
        self.assertIsNotNone(error, 'unexpected initial ledger must reject mutation')

    def test_first_publication_preserves_competing_regular_file_and_symlink(self):
        import os
        for competing_symlink in (False, True):
            with self.subTest(symlink=competing_symlink), tempfile.TemporaryDirectory() as root:
                engine = Engine(root, "actual-user")
                engine.directory.mkdir()
                target = Path(root) / "foreign.csv"
                sentinel = b"foreign ledger must survive first publication"
                target.write_bytes(sentinel)
                fsync = os.fsync
                appeared = False

                def appear_after_pending_sync(descriptor):
                    nonlocal appeared
                    result = fsync(descriptor)
                    if not appeared and __import__('stat').S_ISREG(os.fstat(descriptor).st_mode):
                        self.assertFalse(engine.path.exists())
                        self.assertEqual(len(list(engine.directory.glob(".pending-*"))), 1)
                        if competing_symlink:
                            engine.path.symlink_to(target)
                        else:
                            engine.path.write_bytes(sentinel)
                        appeared = True
                    return result

                error = None
                with patch("performance.os.fsync", side_effect=appear_after_pending_sync):
                    try:
                        engine.set_enabled(self.session, True)
                    except (ValueError, OSError) as caught:
                        error = caught
                self.assertTrue(appeared, "competition immediately before publication was not exercised")
                self.assertEqual(engine.path.is_symlink(), competing_symlink)
                self.assertEqual(engine.path.read_bytes(), sentinel)
                self.assertEqual(target.read_bytes(), sentinel)
                self.assertEqual(list(engine.directory.iterdir()), [engine.path],
                                 "first-publication failure leaked a pending file")
                self.assertIsNotNone(error, "competing ledger must reject initial publication")

    @unittest.skipUnless(__import__("os").name == "posix", "requires POSIX hard-link publication")
    def test_first_publication_link_failure_leaves_no_partial_ledger_or_pending_file(self):
        self.engine.directory.mkdir()
        for failure in (OSError("hard links unavailable"), NotImplementedError("dir_fd unavailable")):
            with self.subTest(failure=type(failure).__name__):
                with patch("performance.os.link", side_effect=failure) as link:
                    with patch("performance.os.replace") as replace:
                        with self.assertRaises(type(failure)):
                            self.enable()
                link.assert_called_once()
                replace.assert_not_called()
                self.assertFalse(self.engine.path.exists())
                self.assertEqual(list(self.engine.directory.iterdir()), [])

    @unittest.skipUnless(__import__("os").name == "posix", "requires POSIX directory fsync")
    def test_first_publication_syncs_root_before_staging_then_file_and_child(self):
        import os
        import stat
        for existing_directory in (False, True):
            with self.subTest(existing_directory=existing_directory), tempfile.TemporaryDirectory() as root:
                engine = Engine(root, "actual-user")
                if existing_directory:
                    engine.directory.mkdir()
                events = []
                fsync, opened, link = os.fsync, os.open, os.link

                def sync(descriptor):
                    info = os.fstat(descriptor)
                    if os.path.samestat(info, engine.root.stat()):
                        events.append("root")
                    elif stat.S_ISREG(info.st_mode):
                        events.append("file")
                    else:
                        events.append("child")
                    return fsync(descriptor)

                def open_file(path, *args, **kwargs):
                    if Path(path).name.startswith(".pending-"):
                        events.append("stage")
                    return opened(path, *args, **kwargs)

                def publish(*args, **kwargs):
                    events.append("publish")
                    return link(*args, **kwargs)

                with patch("performance.os.fsync", side_effect=sync), patch(
                        "performance.os.open", side_effect=open_file), patch(
                        "performance.os.link", side_effect=publish):
                    engine.set_enabled(self.session, True)
                self.assertEqual(events, ["root", "stage", "file", "publish", "child"])

    @unittest.skipUnless(__import__("os").name == "posix", "requires POSIX directory fsync")
    def test_first_publication_root_sync_failure_has_no_partial_write_and_can_retry(self):
        import os
        fsync = os.fsync
        root_syncs = []

        def fail_root_sync(descriptor):
            if os.path.samestat(os.fstat(descriptor), self.root.stat()):
                root_syncs.append(descriptor)
                raise OSError("root sync failed")
            return fsync(descriptor)

        for attempt in range(2):
            with self.subTest(attempt=attempt), patch(
                    "performance.os.fsync", side_effect=fail_root_sync):
                with self.assertRaisesRegex(OSError, "root sync failed"):
                    self.enable()
            self.assertFalse(self.engine.path.exists())
            self.assertEqual(list(self.engine.directory.iterdir()), [])
        self.assertEqual(len(root_syncs), 2, "retry must sync an already existing empty directory's parent")
        self.enable()
        self.assertTrue(self.engine.status(self.session)["enabled"])

    @unittest.skipUnless(__import__("os").name == "posix", "requires POSIX directory fsync")
    def test_first_publication_child_sync_failure_leaves_complete_replayable_ledger(self):
        import os
        fsync = os.fsync

        def fail_child_sync(descriptor):
            if os.path.samestat(os.fstat(descriptor), self.engine.directory.stat()):
                self.assertTrue(self.engine.path.exists())
                raise OSError("child sync failed")
            return fsync(descriptor)

        with patch("performance.os.fsync", side_effect=fail_child_sync):
            with self.assertRaisesRegex(OSError, "child sync failed"):
                self.enable()
        self.assertEqual(list(self.engine.directory.iterdir()), [self.engine.path])
        self.assertTrue(Engine(self.root, "actual-user").status(self.session)["enabled"])
        before = self.engine.path.read_bytes()
        self.enable()
        self.assertEqual(self.engine.path.read_bytes(), before)

    @unittest.skipUnless(__import__("os").name == "posix", "requires POSIX directory fsync")
    def test_noop_mutation_retry_confirms_namespace_without_rewriting_visible_history(self):
        import os
        for operation in ("set_enabled", "assess", "assessment_transition", "adopt_policy", "import_history"):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as root:
                engine = Engine(root, "actual-user")
                if operation.startswith("assess"):
                    engine.set_enabled(self.session, True)
                    count = 5 if operation == "assessment_transition" else 1
                    runs = [engine.prepare(self.session, "codex", "executor", "low",
                                           MODELS, list(range(7))) for _ in range(count)]
                    def assess(run):
                        return engine.assess(run["run_id"], 4, run["model_id"], run["effort"],
                                             "exec-" + run["run_id"], verified=True)
                    for run in runs[:-1]:
                        assess(run)
                    mutate = lambda: assess(runs[-1])
                elif operation == "set_enabled":
                    mutate = lambda: engine.set_enabled(self.session, True)
                elif operation == "adopt_policy":
                    mutate = engine.adopt_policy
                else:
                    mutate = lambda: engine.import_history([{"score": "4", "model_slug": "old"}])
                fsync = os.fsync
                child_syncs = []

                def fail_child_sync(descriptor):
                    if os.path.samestat(os.fstat(descriptor), engine.directory.stat()):
                        child_syncs.append(descriptor)
                        raise OSError("namespace durability unconfirmed")
                    return fsync(descriptor)

                with patch("performance.os.fsync", side_effect=fail_child_sync):
                    with self.assertRaisesRegex(OSError, "namespace durability unconfirmed"):
                        mutate()
                visible = engine.path.read_bytes()
                self.assertEqual(list(engine.directory.iterdir()), [engine.path])
                with patch("performance.os.fsync", side_effect=fail_child_sync):
                    engine.status(self.session)
                self.assertEqual(len(child_syncs), 1, "status must remain read-only")
                with patch("performance.os.fsync", side_effect=fail_child_sync):
                    with self.assertRaisesRegex(OSError, "namespace durability unconfirmed"):
                        mutate()
                self.assertEqual(len(child_syncs), 2)
                self.assertEqual(engine.path.read_bytes(), visible)
                recovered_syncs = []

                def recover_sync(descriptor):
                    self.assertTrue(os.path.samestat(os.fstat(descriptor), engine.directory.stat()))
                    self.assertEqual(engine.path.read_bytes(), visible)
                    recovered_syncs.append(descriptor)
                    return fsync(descriptor)

                with patch("performance.os.fsync", side_effect=recover_sync), patch(
                        "performance.os.replace") as replace, patch("performance.os.link") as link:
                    result = mutate()
                self.assertEqual(len(recovered_syncs), 1)
                replace.assert_not_called()
                link.assert_not_called()
                self.assertEqual(engine.path.read_bytes(), visible)
                if operation == "assessment_transition":
                    self.assertEqual(result["transition"]["step"], 1)
                elif operation == "assess":
                    self.assertTrue(result["eligible"])
                elif operation == "import_history":
                    self.assertTrue(result["duplicate"])
                elif operation == "adopt_policy":
                    self.assertFalse(result["changed"])
                else:
                    self.assertTrue(result["enabled"])

    @unittest.skipUnless(__import__("os").name == "posix", "requires POSIX hard-link publication")
    def test_cli_first_publication_unsupported_link_reports_compact_error_and_can_retry(self):
        import io
        import performance
        command = ["--root", str(self.root), "--user", "actual-user",
                   "--session", self.session, "on"]
        output, errors = io.StringIO(), io.StringIO()
        with patch("performance.os.link", side_effect=NotImplementedError("link unsupported")), patch(
                "sys.stdout", output), patch("sys.stderr", errors):
            result = performance.main(command)
        self.assertEqual(result, 1)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(errors.getvalue(), "error: link unsupported\n")
        self.assertFalse(self.engine.path.exists())
        self.assertEqual(list(self.engine.directory.iterdir()), [])
        with patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
            self.assertEqual(performance.main(command), 0)
        self.assertTrue(self.engine.status(self.session)["enabled"])

    def test_ledger_directory_appearing_after_absent_load_is_not_overwritten(self):
        self.assertFalse(self.engine.status(self.session)['enabled'])
        self.assertFalse(self.engine.directory.exists(), 'status must preserve absent directory')
        sentinel = b'concurrently appeared ledger must remain untouched'
        load = self.engine._load
        appeared = False
        def appear_after_load(root_fd=None):
            nonlocal appeared
            rows = load(root_fd)
            self.engine.directory.mkdir()
            self.engine.path.write_bytes(sentinel)
            appeared = True
            return rows
        error = None
        with patch.object(self.engine, '_load', side_effect=appear_after_load):
            try:
                self.engine.set_enabled(self.session, True)
            except (ValueError, OSError) as caught:
                error = caught
        self.assertTrue(appeared, 'directory appearance after absent load was not exercised')
        self.assertEqual(self.engine.path.read_bytes(), sentinel,
                         'transaction overwrote a directory that appeared after its absent read')
        self.assertEqual(list(self.engine.directory.iterdir()), [self.engine.path])
        self.assertIsNotNone(error, 'concurrent directory appearance must reject mutation')

    @unittest.skipUnless(__import__('os').name == 'posix', 'requires POSIX directory rename while open')
    def test_ledger_directory_replaced_after_load_cannot_receive_stale_commit(self):
        self.enable()
        original = self.engine.path.read_bytes()
        retained = self.root / 'retained-model-perf'
        sentinel = b'replacement ledger must remain untouched'
        load = self.engine._load
        swapped = False
        def replace_after_load(root_fd=None):
            nonlocal swapped
            rows = load(root_fd)
            self.engine.directory.rename(retained)
            self.engine.directory.mkdir()
            self.engine.path.write_bytes(sentinel)
            swapped = True
            return rows
        error = None
        with patch.object(self.engine, '_load', side_effect=replace_after_load):
            try:
                self.engine.set_enabled(self.session, False)
            except (ValueError, OSError) as caught:
                error = caught
        self.assertTrue(swapped, 'replacement between load and commit was not exercised')
        self.assertEqual((retained / self.engine.path.name).read_bytes(), original)
        self.assertEqual(self.engine.path.read_bytes(), sentinel,
                         'stale transaction replaced a ledger in a substituted directory')
        self.assertEqual([path.name for path in self.engine.directory.iterdir()],
                         [self.engine.path.name], 'pending file leaked in replacement directory')
        self.assertIsNotNone(error, 'directory replacement must reject the stale mutation')

    def test_project_root_replaced_before_lock_preserves_both_ledgers(self):
        self.enable()
        original = self.engine.path.read_bytes()
        with tempfile.TemporaryDirectory() as retained_name:
            retained = Path(retained_name) / 'project'
            self.root.rename(retained)
            self.root.mkdir()
            self.engine.directory.mkdir()
            self.engine.path.write_bytes(original)
            try:
                with self.assertRaisesRegex(ValueError, 'project root'):
                    self.engine.set_enabled(self.session, False)
                self.assertEqual(self.engine.path.read_bytes(), original)
                self.assertEqual((retained / 'model-perf' / self.engine.path.name).read_bytes(), original)
            finally:
                self.engine.path.unlink()
                self.engine.directory.rmdir()
                self.root.rmdir()
                retained.rename(self.root)

    @unittest.skipUnless(__import__('os').name == 'posix', 'requires POSIX directory descriptors')
    def test_status_rejects_root_removed_between_load_and_directory_checks(self):
        self.enable()
        original = self.engine.path.read_bytes()
        with tempfile.TemporaryDirectory() as retained_name:
            retained = Path(retained_name) / 'project'
            check = self.engine._check_root_identity
            checks = 0
            swapped = False
            def remove_after_load_check(root_fd=None):
                nonlocal checks, swapped
                check(root_fd)
                checks += 1
                if checks == 3:
                    self.root.rename(retained)
                    swapped = True
            error = None
            try:
                with patch.object(self.engine, '_check_root_identity',
                                  side_effect=remove_after_load_check):
                    try:
                        self.engine.status(self.session)
                    except (ValueError, OSError) as caught:
                        error = caught
                self.assertTrue(swapped, 'root removal between load checks was not exercised')
                self.assertEqual((retained / 'model-perf' / self.engine.path.name).read_bytes(), original)
                self.assertIsNotNone(error, 'missing project root must not become an empty ledger')
            finally:
                if swapped:
                    retained.rename(self.root)

    @unittest.skipUnless(__import__('os').name == 'posix', 'requires POSIX directory symlinks')
    def test_project_root_swapped_after_pending_sync_preserves_ledgers_and_cleans_temp(self):
        import os
        self.enable()
        original = self.engine.path.read_bytes()
        with tempfile.TemporaryDirectory() as attack_name:
            attack = Path(attack_name)
            retained = attack / 'retained'
            outside = attack / 'outside'
            (outside / 'model-perf').mkdir(parents=True)
            external_ledger = outside / 'model-perf' / self.engine.path.name
            external_ledger.write_bytes(b'outside sentinel')
            real_sync = os.fsync
            swapped = False
            def swap(descriptor):
                nonlocal swapped
                real_sync(descriptor)
                if not swapped:
                    self.root.rename(retained)
                    self.root.symlink_to(outside, target_is_directory=True)
                    swapped = True
            try:
                with patch('performance.os.fsync', side_effect=swap):
                    with self.assertRaisesRegex(ValueError, 'project root'):
                        self.engine.set_enabled(self.session, False)
                self.assertTrue(swapped, 'pending sync substitution was not exercised')
                self.assertEqual(external_ledger.read_bytes(), b'outside sentinel')
                ledger_directory = retained / 'model-perf'
                self.assertEqual((ledger_directory / self.engine.path.name).read_bytes(), original)
                self.assertEqual([path.name for path in ledger_directory.iterdir()],
                                 [self.engine.path.name], 'pending file leaked in original project')
                self.assertEqual([path.name for path in (outside / 'model-perf').iterdir()],
                                 [self.engine.path.name], 'pending file escaped to outside project')
            finally:
                if swapped:
                    self.root.unlink()
                    retained.rename(self.root)

    @unittest.skipUnless(__import__('os').name == 'posix', 'requires POSIX directory symlinks')
    def test_project_root_swapped_after_lock_validation_cannot_write_outside_project(self):
        self.enable()
        original_ledger = self.engine.path.read_bytes()
        with tempfile.TemporaryDirectory() as attack_name:
            attack = Path(attack_name)
            retained = attack / 'retained-project'
            outside = attack / 'outside'
            outside_directory = outside / 'model-perf'
            outside_directory.mkdir(parents=True)
            outside_ledger = outside_directory / self.engine.path.name
            outside_ledger.write_bytes(original_ledger)
            sentinel = outside / 'sentinel'
            sentinel.write_bytes(b'outside sentinel must remain untouched')
            before = {str(path.relative_to(outside)): path.read_bytes()
                      for path in outside.rglob('*') if path.is_file()}
            original_check = self.engine._safe_paths
            swapped = False

            def swap_after_lock_validation():
                nonlocal swapped
                original_check()
                if not swapped:
                    self.root.rename(retained)
                    self.root.symlink_to(outside, target_is_directory=True)
                    swapped = True

            error = None
            try:
                with patch.object(self.engine, '_safe_paths', side_effect=swap_after_lock_validation):
                    try:
                        self.engine.set_enabled(self.session, False)
                    except (ValueError, OSError) as caught:
                        error = caught
                self.assertTrue(swapped, 'project-root substitution was not exercised')
                self.assertEqual((retained / 'model-perf' / self.engine.path.name).read_bytes(),
                                 original_ledger, 'original project ledger was changed')
                self.assertEqual(
                    {str(path.relative_to(outside)): path.read_bytes()
                     for path in outside.rglob('*') if path.is_file()}, before,
                    'mutation followed a project root replaced by an outside symlink')
                self.assertIsNotNone(error, 'project-root substitution must reject the mutation')
            finally:
                if swapped:
                    self.root.unlink()
                    retained.rename(self.root)

    @unittest.skipUnless(__import__('os').name == 'posix', 'requires POSIX directory symlinks')
    def test_directory_swapped_after_commit_validation_cannot_write_outside_project(self):
        self.enable()
        original_ledger = self.engine.path.read_bytes()
        retained = self.root / 'retained-model-perf'
        with tempfile.TemporaryDirectory() as outside_name:
            outside = Path(outside_name)
            outside_ledger = outside / self.engine.path.name
            outside_ledger.write_bytes(b'outside ledger must remain untouched')
            before = {path.name: path.read_bytes() for path in outside.iterdir()}
            original_check = self.engine._safe_paths
            checks = 0
            swapped = False

            def swap_after_second_check():
                nonlocal checks, swapped
                original_check()
                checks += 1
                if checks == 2:
                    self.engine.directory.rename(retained)
                    self.engine.directory.symlink_to(outside, target_is_directory=True)
                    swapped = True

            error = None
            with patch.object(self.engine, '_safe_paths', side_effect=swap_after_second_check):
                try:
                    self.engine.set_enabled(self.session, False)
                except (ValueError, OSError) as caught:
                    error = caught

            self.assertTrue(swapped, 'commit validation swap was not exercised')
            self.assertEqual(
                {path.name: path.read_bytes() for path in outside.iterdir()}, before,
                'commit followed a model-perf directory replaced by an outside symlink')
            self.assertEqual((retained / self.engine.path.name).read_bytes(), original_ledger)
            self.assertIsNotNone(error, 'directory substitution must reject the mutation')

    @unittest.skipUnless(__import__('os').name == 'posix', 'requires POSIX directory symlinks')
    def test_directory_swapped_after_pending_write_aborts_and_cleans_anchored_temp(self):
        import os
        self.enable()
        original_ledger = self.engine.path.read_bytes()
        retained = self.root / 'retained-model-perf'
        with tempfile.TemporaryDirectory() as outside_name:
            outside = Path(outside_name)
            original_fsync = os.fsync
            swapped = False
            def swap_after_flush(descriptor):
                nonlocal swapped
                original_fsync(descriptor)
                if not swapped:
                    self.engine.directory.rename(retained)
                    self.engine.directory.symlink_to(outside, target_is_directory=True)
                    swapped = True
            error = None
            with patch('performance.os.fsync', side_effect=swap_after_flush):
                try:
                    self.engine.set_enabled(self.session, False)
                except (ValueError, OSError) as caught:
                    error = caught
            self.assertTrue(swapped, 'pending-write swap was not exercised')
            self.assertEqual(list(outside.iterdir()), [], 'publication escaped the pinned directory')
            self.assertEqual((retained / self.engine.path.name).read_bytes(), original_ledger)
            self.assertEqual(sorted(path.name for path in retained.iterdir()), [self.engine.path.name],
                             'failed publication left a pending file in the pinned directory')
            self.assertIsNotNone(error, 'directory substitution must reject the mutation')

    @unittest.skipUnless(__import__('os').name == 'posix', 'requires POSIX directory symlinks')
    def test_status_rejects_parent_directory_swapped_after_validation(self):
        self.enable()
        original = self.engine.path.read_bytes()
        retained = self.root / 'retained-model-perf'
        with tempfile.TemporaryDirectory() as outside_name:
            outside = Path(outside_name)
            (outside / self.engine.path.name).write_bytes(original)
            check = self.engine._safe_paths
            swapped = False
            def swap():
                nonlocal swapped
                check()
                self.engine.directory.rename(retained)
                self.engine.directory.symlink_to(outside, target_is_directory=True)
                swapped = True
            with patch.object(self.engine, '_safe_paths', side_effect=swap):
                with self.assertRaises((ValueError, OSError)):
                    self.engine.status(self.session)
            self.assertTrue(swapped)
            self.assertEqual((outside / self.engine.path.name).read_bytes(), original)
            self.assertEqual((retained / self.engine.path.name).read_bytes(), original)

    @unittest.skipUnless(__import__('os').name == 'posix', 'requires POSIX directory descriptors')
    def test_directory_guard_closes_and_cleans_pending_after_write_interruption(self):
        import os
        self.enable()
        original = self.engine.path.read_bytes()
        for failure in (OSError('sync failed'), KeyboardInterrupt()):
            with self.subTest(failure=type(failure).__name__):
                descriptors = []
                real_open = os.open
                def opened(*args, **kwargs):
                    descriptor = real_open(*args, **kwargs)
                    if (args[0] == self.engine.directory.name
                            and kwargs.get('dir_fd') is not None):
                        descriptors.append(descriptor)
                    return descriptor
                with patch('performance.os.open', side_effect=opened), \
                        patch('performance.os.fsync', side_effect=failure):
                    with self.assertRaises(type(failure)):
                        self.engine.set_enabled(self.session, False)
                self.assertTrue(descriptors)
                for descriptor in descriptors:
                    with self.assertRaises(OSError):
                        os.fstat(descriptor)
                self.assertEqual(self.engine.path.read_bytes(), original)
                self.assertEqual(list(self.engine.directory.iterdir()), [self.engine.path])

    @unittest.skipUnless(hasattr(__import__('os'), 'mkfifo') and hasattr(__import__('os'), 'O_NONBLOCK'),
                         'requires FIFO and nonblocking open support')
    def test_fifo_swapped_after_path_validation_does_not_block_status(self):
        self.enable()
        code = '''
import os, sys
from performance import Engine
engine = Engine(sys.argv[1], "actual-user")
original = engine._safe_paths
def swap():
    original()
    engine.path.unlink()
    os.mkfifo(engine.path)
engine._safe_paths = swap
try:
    engine.status("session-a")
except ValueError as error:
    print(error)
else:
    sys.exit("status accepted FIFO")
'''
        try:
            result = subprocess.run(
                [sys.executable, '-c', code, str(self.root)],
                env={**__import__('os').environ, 'PYTHONPATH': str(SCRIPT.parent)},
                capture_output=True, text=True, timeout=2)
        except subprocess.TimeoutExpired:
            self.fail('status blocked opening a FIFO swapped in after path validation')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('ledger must be a regular file', result.stdout)

    @unittest.skipUnless(hasattr(__import__('os'), 'mkfifo') and hasattr(__import__('os'), 'O_NONBLOCK'),
                         'requires FIFO and nonblocking open support')
    def test_nonregular_descriptor_rejected_before_csv_and_closed(self):
        import os
        self.enable()
        self.engine.path.unlink()
        os.mkfifo(self.engine.path)
        descriptor = os.open(self.engine.path, os.O_RDONLY | os.O_NONBLOCK)
        original_open = os.open
        def open_ledger_only(path, *args, **kwargs):
            if path == self.engine.path.name:
                return descriptor
            return original_open(path, *args, **kwargs)
        with patch('performance.os.open', side_effect=open_ledger_only), \
             patch('performance.csv.DictReader') as reader:
            with self.assertRaisesRegex(ValueError, 'ledger must be a regular file'):
                self.engine._load()
            reader.assert_not_called()
        with self.assertRaises(OSError):
            os.fstat(descriptor)

    @unittest.skipUnless(hasattr(__import__('os'), 'O_NONBLOCK'), 'flag already unavailable')
    def test_regular_ledger_reads_when_nonblock_flag_unavailable(self):
        import os
        self.enable()
        with patch.object(os, 'O_NONBLOCK'):
            del os.O_NONBLOCK
            self.assertTrue(self.engine.status(self.session)['enabled'])

    def test_foreign_identity_schema_policy_and_sequence_fail_closed(self):
        self.enable()
        original = self.engine.path.read_text()
        for key, value in (("root", "/different/project"), ("user_id", "other-user"),
                           ("policy_version", "future-policy")):
            rows = self.events()
            rows[0]["data"][key] = value
            self.write_events(rows)
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.engine.status(self.session)
            self.engine.path.write_text(original)
        rows = self.events()
        rows[0]["schema_version"] = "999"
        self.write_events(rows)
        with self.assertRaises(ValueError):
            self.engine.status(self.session)
        self.engine.path.write_text(original)
        rows = self.events()
        rows[-1]["sequence"] = "999"
        self.write_events(rows)
        with self.assertRaises(ValueError):
            self.enable()

    def write_events(self, rows):
        with self.engine.path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(dict(row, data=json.dumps(row["data"])) for row in rows)

    def test_parallel_processes_preserve_unique_runs_and_contiguous_events(self):
        self.enable()
        with ProcessPoolExecutor(max_workers=4) as executor:
            runs = list(executor.map(parallel_prepare,
                                     [(str(self.root), "actual-user", self.session)] * 12))
        self.assertEqual(len({run["run_id"] for run in runs}), 12)
        events = self.events()
        self.assertEqual(sum(row["event_type"] == "launch" for row in events), 12)
        self.assertEqual([int(row["sequence"]) for row in events], list(range(1, len(events) + 1)))

    def test_parallel_assessments_never_double_advance(self):
        self.enable()
        runs = [self.prepare() for _ in range(5)]
        with ProcessPoolExecutor(max_workers=4) as executor:
            list(executor.map(parallel_assess, [(str(self.root), run) for run in runs]))
        self.assertEqual(sum(row["event_type"] == "transition" for row in self.events()), 2)
        self.assertEqual(self.engine.status(self.session)["tracks"][0]["step"], 1)

    def test_invalid_payloads_are_rejected_without_mutation(self):
        self.enable()
        run = self.prepare()
        before = self.engine.path.read_bytes()
        for overrides in ({"score": True}, {"score": 6}, {"verified": "yes"},
                          {"execution_id": ""}, {"effective_effort": ""},
                          {"run_id": "missing"}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.assess(run, **overrides)
        for overrides in ({"available_steps": [0, 0]}, {"models": {"terra": "only"}},
                          {"tier": "unknown"}, {"mode": "claude-ultracode"},
                          {"role": "advisor", "tier": "business_doc"}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.prepare(**overrides)
        self.assertEqual(before, self.engine.path.read_bytes())

    def test_legacy_import_is_lossless_idempotent_and_never_eligible(self):
        rows = [{"timestamp": "old", "model_slug": "sol", "reasoning_effort": "unknown",
                 "score": "4", "task_complexity": "unknown"}] * 2
        result = self.engine.import_history(rows)
        self.assertEqual(result["imported_count"], 2)
        self.assertFalse(result["eligible"])
        self.assertFalse(self.engine.status(self.session)["enabled"])
        before = self.engine.path.read_bytes()
        self.assertTrue(self.engine.import_history(rows)["duplicate"])
        self.assertEqual(self.engine.path.read_bytes(), before)
        self.assertEqual(self.events()[-1]["data"]["rows"], rows)

    def test_replay_rejects_corrupt_legacy_import_before_read_or_retry(self):
        imported = [{"score": "5", "arbitrary": [None, True, {"value": 3}]}]
        self.engine.import_history(imported)
        original = self.engine.path.read_bytes()
        for case in ("changed_rows", "non_object_row", "duplicate_digest"):
            for operation in ("status", "retry"):
                with self.subTest(case=case, operation=operation):
                    self.engine.path.write_bytes(original)
                    events = self.events()
                    entry = events[-1]["data"]
                    if case == "changed_rows":
                        entry["rows"][0]["score"] = "0"
                    elif case == "non_object_row":
                        entry["rows"] = ["not an object"]
                    else:
                        self.engine._append(events, "legacy_import", dict(entry))
                    self.write_events(events)
                    corrupted = self.engine.path.read_bytes()
                    with self.assertRaises(ValueError):
                        if operation == "status":
                            self.engine.status(self.session)
                        else:
                            self.engine.import_history(imported)
                    self.assertEqual(self.engine.path.read_bytes(), corrupted)

    def test_corrupt_truncated_data_and_projected_fields_fail_without_clobber(self):
        self.enable()
        self.prepare()
        original = self.engine.path.read_bytes()
        for corrupted in (original[:-17], original.replace(b'"session"', b'"unknown"', 1)):
            self.engine.path.write_bytes(corrupted)
            with self.assertRaises((ValueError, csv.Error)):
                self.prepare()
            self.assertEqual(self.engine.path.read_bytes(), corrupted)
        self.engine.path.write_bytes(original)
        rows = self.events()
        rows[-1]["role"] = "advisor"
        self.write_events(rows)
        before = self.engine.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "projection"):
            self.enable()
        self.assertEqual(self.engine.path.read_bytes(), before)

    def test_failed_atomic_replace_preserves_state_and_cleans_temporary(self):
        self.enable()
        before = self.engine.path.read_bytes()
        with patch("performance.os.replace", side_effect=PermissionError("write denied")):
            with self.assertRaises(PermissionError):
                self.prepare()
        self.assertEqual(self.engine.path.read_bytes(), before)
        self.assertEqual(self.engine.status(self.session)["tracks"], [])
        self.assertEqual([path.name for path in self.engine.directory.iterdir()],
                         ["actual-user-model-perf.csv"])

    def test_corrupt_valid_json_assessment_attribution_is_rejected(self):
        self.enable()
        self.assess(self.prepare())
        rows = self.events()
        rows[-1]["data"]["attribution"]["model_id"] = "invented-model"
        self.write_events(rows)
        before = self.engine.path.read_bytes()
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual(self.engine.path.read_bytes(), before)

    def test_replay_rejects_malformed_assessment_fields_without_mutation(self):
        self.enable()
        self.assess(self.prepare(), score=1)
        original = self.engine.path.read_bytes()
        cases = (
            ("request verified string", "request", "verified", "false"),
            ("request execution empty", "request", "execution_id", ""),
            ("request score boolean", "request", "score", True),
            ("attribution verified integer", "attribution", "verified", 1),
            ("attribution score boolean", "attribution", "score", True),
            ("result eligible integer", "result", "eligible", 1),
        )
        for label, section, field, value in cases:
            with self.subTest(case=label):
                self.engine.path.write_bytes(original)
                rows = self.events()
                rows[-1]["data"][section][field] = value
                self.write_events(rows)
                corrupted = self.engine.path.read_bytes()
                with self.assertRaises(ValueError):
                    self.engine.status(self.session)
                self.assertEqual(self.engine.path.read_bytes(), corrupted)

    def test_model_rollover_resets_before_old_window_can_downshift(self):
        self.enable()
        for _ in range(5):
            self.assess(self.prepare(available_steps=[1, 2, 3]), score=5)
        previous = self.engine.status(self.session)["tracks"][0]
        self.assertEqual(previous["step"], 1)
        current = self.prepare(models={"terra": "terra-v2", "sol": "sol-v2"})
        self.assertEqual((current["step"], current["model_id"]), (1, "terra-v2"))
        self.assertNotEqual(current["epoch"], previous["epoch"])

    def test_provider_execution_ids_are_namespaced_across_platforms(self):
        self.enable()
        codex = self.prepare()
        claude = self.prepare(platform="claude", models=CLAUDE_MODELS, available_steps=list(range(6)))
        self.assertTrue(self.assess(codex, execution_id="provider-local-42")["eligible"])
        self.assertTrue(self.assess(claude, execution_id="provider-local-42")["eligible"])
        same_platform = self.prepare(role="advisor", tier=None, available_steps=[0, 1])
        self.assertFalse(self.assess(same_platform, execution_id="provider-local-42")["eligible"])

    def test_advisor_omitted_tier_uses_one_durable_track_and_supplied_tier_is_rejected(self):
        self.enable()
        first = self.engine.prepare(self.session, "codex", "advisor",
                                    models=MODELS, available_steps=[0, 1])
        second = Engine(self.root, "actual-user").prepare(
            self.session, "codex", "advisor", None, MODELS, [0, 1])
        self.assertIsNone(first["tier"])
        self.assertEqual(first["epoch"], second["epoch"])
        self.assertEqual(len(self.engine.status(self.session)["tracks"]), 1)
        for tier in ("low", "medium", "high", "business_doc"):
            with self.subTest(tier=tier), self.assertRaisesRegex(ValueError, "advisor"):
                self.prepare(role="advisor", tier=tier, available_steps=[0, 1])

    def test_schema_one_is_read_only_until_lossless_atomic_upgrade_on_next_write(self):
        self.engine.import_history([{"model_slug": "old", "score": "4"}])
        self.enable()
        advisor = self.engine.prepare(self.session, "codex", "advisor",
                                      models=MODELS, available_steps=[0, 1])
        original_events = self.events()
        legacy_fields = [field for field in original_events[0] if field != "tier"]
        with self.engine.path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=legacy_fields)
            writer.writeheader()
            for event in original_events:
                writer.writerow({field: ("1" if field == "schema_version" else
                                         json.dumps(event[field]) if field == "data" else event[field])
                                 for field in legacy_fields})
        legacy_bytes = self.engine.path.read_bytes()
        restarted = Engine(self.root, "actual-user")
        self.assertTrue(restarted.status(self.session)["enabled"])
        self.assertEqual(self.engine.path.read_bytes(), legacy_bytes)
        restarted.set_enabled(self.session, True)  # Idempotent command is read-only.
        self.assertEqual(self.engine.path.read_bytes(), legacy_bytes)
        with patch("performance.os.replace", side_effect=PermissionError("upgrade denied")):
            with self.assertRaises(PermissionError):
                restarted.prepare(self.session, "codex", "executor", "medium", MODELS, list(range(7)))
        self.assertEqual(self.engine.path.read_bytes(), legacy_bytes)
        launched = restarted.prepare(self.session, "codex", "executor", "medium", MODELS, list(range(7)))
        upgraded = self.events()
        for old, current in zip(original_events, upgraded):
            self.assertEqual({key: value for key, value in old.items() if key not in ("schema_version", "tier")},
                             {key: value for key, value in current.items() if key not in ("schema_version", "tier")})
        self.assertEqual({event["schema_version"] for event in upgraded}, {"2"})
        self.assertEqual(upgraded[-1]["tier"], "medium")
        self.assertEqual(upgraded[-1]["role"], "executor")
        self.assertEqual(upgraded[-1]["run_id"], launched["run_id"])
        advisor_event = next(event for event in upgraded if event["run_id"] == advisor["run_id"])
        self.assertEqual(advisor_event["tier"], "")
        self.assertEqual(upgraded[0]["tier"], "")
        self.assertEqual(upgraded[1]["tier"], "")

    def test_corrupt_tier_projection_is_rejected_without_clobber(self):
        self.enable()
        self.prepare()
        rows = self.events()
        rows[-1]["tier"] = "high"
        self.write_events(rows)
        before = self.engine.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "projection"):
            self.prepare()
        self.assertEqual(self.engine.path.read_bytes(), before)

    def test_sequential_v1_v2_v3_v4_adoption_preserves_history_and_retires_changed_roles(self):
        old_executor = write_policy_one_fixture(self.engine, self.session)
        before = self.engine.path.read_bytes()
        historical = self.events()
        status = self.engine.status(self.session)
        self.assertEqual(status["policy_version"], "optimal-ultra-ladder-v1")
        self.assertEqual(self.engine.path.read_bytes(), before)
        adopted = self.engine.adopt_policy()
        self.assertTrue(adopted["changed"])
        self.assertEqual(adopted["policy_version"], "optimal-ultra-ladder-v4")
        self.assertEqual([row["data"]["to_policy_version"] for row in self.events()
                          if row["event_type"] == "policy_adoption"],
                         ["optimal-ultra-ladder-v2", "optimal-ultra-ladder-v3", "optimal-ultra-ladder-v4"])
        self.assertEqual(self.events()[:len(historical)], historical)
        after = self.engine.path.read_bytes()
        self.assertFalse(self.engine.adopt_policy()["changed"])
        self.assertEqual(self.engine.path.read_bytes(), after)
        tracks = self.engine.status(self.session)["tracks"]
        self.assertEqual(tracks, [])
        fresh = self.engine.prepare(self.session, "codex", "executor", "medium",
                                    {"terra": "terra-new", "sol": "sol-new"}, list(range(7)))
        self.assertEqual((fresh["step"], fresh["family"], fresh["effort"]), (1, "terra", "medium"))
        self.assertNotEqual(fresh["epoch"], old_executor["epoch"])
        late = self.assess(old_executor)
        self.assertFalse(late["eligible"])
        self.assertIn("policy_changed", late["exclusions"])
        self.assertIsNone(late["transition"])
        old_advisor = next(row["data"] for row in historical
                           if row["event_type"] == "launch" and row["run_id"] == "advisor-3")
        self.assertIn("policy_changed", self.assess(old_advisor)["exclusions"])
        current_advisor = self.engine.prepare(self.session, "codex", "advisor",
                                              models={"sol": "sol-old"}, available_steps=[0, 1])
        self.assertNotEqual(current_advisor["epoch"], "advisor-v1")
        self.assertIsNone(self.assess(current_advisor)["transition"])

    def test_prepare_adopts_policy_atomically_and_unknown_policy_fails_closed(self):
        write_policy_one_fixture(self.engine, self.session)
        before = self.engine.path.read_bytes()
        with patch("performance.os.replace", side_effect=PermissionError("adoption denied")):
            with self.assertRaises(PermissionError):
                self.engine.prepare(self.session, "codex", "executor", "medium",
                                    {"terra": "terra-new", "sol": "sol-new"}, list(range(7)))
        self.assertEqual(self.engine.path.read_bytes(), before)
        self.engine.prepare(self.session, "codex", "executor", "medium",
                            {"terra": "terra-new", "sol": "sol-new"}, list(range(7)))
        self.assertEqual(sum(row["event_type"] == "policy_adoption" for row in self.events()), 3)
        events = self.events()
        events[0]["data"]["policy_version"] = "unknown-policy"
        self.write_events(events)
        corrupted = self.engine.path.read_bytes()
        with self.assertRaises(ValueError):
            self.engine.adopt_policy()
        self.assertEqual(self.engine.path.read_bytes(), corrupted)

    def test_adoption_without_launch_retains_old_executor_receipt_as_excluded_history(self):
        old = write_policy_one_fixture(self.engine, self.session)
        self.engine.adopt_policy()
        outcome = self.assess(old)
        self.assertFalse(outcome["eligible"])
        self.assertIn("policy_changed", outcome["exclusions"])
        status = Engine(self.root, "actual-user").status(self.session)
        self.assertTrue(status["enabled"])
        self.assertEqual(status["tracks"], [])

    def test_cli_explicit_adoption_is_idempotent_and_does_not_launch(self):
        write_policy_one_fixture(self.engine, self.session)
        launches = sum(event["event_type"] == "launch" for event in self.events())
        command = [sys.executable, str(SCRIPT), "--root", str(self.root), "--user",
                   "actual-user", "--session", self.session, "adopt-policy"]
        first = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(json.loads(first.stdout),
                         {"changed": True, "policy_version": "optimal-ultra-ladder-v4"})
        before = self.engine.path.read_bytes()
        second = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertFalse(json.loads(second.stdout)["changed"])
        self.assertEqual(self.engine.path.read_bytes(), before)
        self.assertEqual(sum(event["event_type"] == "launch" for event in self.events()), launches)

    def test_advisor_context_floor_raises_fresh_epoch_and_lowering_only_relaxes(self):
        self.enable()
        first = self.engine.prepare(self.session, "codex", "advisor", models={"sol": "sol-v1", "astra": "astra-v1"},
                                    available_steps=[0, 1, 2])
        raised = self.engine.prepare(self.session, "codex", "advisor", models={"sol": "sol-v1", "astra": "astra-v1"},
                                     available_steps=[0, 1, 2], advice_level="super_high")
        self.assertEqual((raised["step"], raised["family"], raised["effort"]), (2, "astra", "max"))
        self.assertNotEqual(first["epoch"], raised["epoch"])
        lowered = self.engine.prepare(self.session, "codex", "advisor", models={"sol": "sol-v1", "astra": "astra-v1"},
                                      available_steps=[0, 1, 2], advice_level="medium")
        self.assertEqual((lowered["step"], lowered["epoch"]), (2, raised["epoch"]))
        self.assertEqual((lowered["advice_level"], lowered["context_floor"]), ("medium", 0))
        restarted = Engine(self.root, "actual-user").status(self.session)
        self.assertEqual(len(restarted["tracks"]), 1)
        self.assertEqual(restarted["tracks"][0]["context_floor"], 0)

    def test_explicit_on_reports_local_instruction_candidate(self):
        instruction = self.root / "AGENTS.md"
        instruction.write_text("All subagents must use the Sol model.\n", encoding="utf-8")
        with patch("os.getcwd", return_value=str(self.root)):
            result = self.engine.set_enabled(self.session, True, platform="codex")
        audit = result.get("instruction_audit")
        self.assertIsNotNone(audit)
        self.assertTrue(any(item["path"] == str(instruction.resolve()) for item in audit["candidates"]))
        self.assertTrue(any(item["category"] == "fixed_helper_model_effort" for item in audit["findings"]))

    def test_explicit_on_always_suggests_without_duplicate_state_or_native_changes(self):
        first = self.engine.set_enabled(self.session, True, platform="claude", complexity="low")
        self.assertEqual(first["orchestrator_suggestion"]["recommendations"][0]["family"], "haiku")
        before = self.engine.path.read_bytes()
        second = self.engine.set_enabled(self.session, True, platform="codex", complexity="high")
        self.assertEqual(second["orchestrator_suggestion"]["recommendations"][0]["family"], "terra")
        self.assertEqual(second["orchestrator_suggestion"]["recommendations"][0]["effort"], "high")
        self.assertFalse(second["orchestrator_suggestion"]["applied"])
        self.assertEqual(self.engine.path.read_bytes(), before)
        unspecified = self.engine.set_enabled(self.session, True)
        recommendations = unspecified["orchestrator_suggestion"]["recommendations"]
        self.assertEqual({item["platform"] for item in recommendations}, {"claude", "codex"})
        self.assertTrue(all(item.get("assumption") for item in recommendations))
        self.assertNotIn("orchestrator_suggestion", self.engine.status(self.session))
        self.assertNotIn("orchestrator_suggestion", self.engine.set_enabled(self.session, False))

    def test_native_context_on_api_and_cli(self):
        context = dict(mode="codex-ultra", active=True, model_id="current", effort="ultra")
        result = self.engine.set_enabled(self.session, True, platform="codex", native_context=context)
        recommendation = result["orchestrator_suggestion"]["recommendations"][0]
        self.assertEqual((recommendation["model_id"], recommendation["effort"]), ("current", "ultra"))
        before = self.engine.path.read_bytes()
        with self.assertRaises(ValueError):
            self.engine.set_enabled(self.session, True, native_context=context)
        with self.assertRaises(ValueError):
            self.engine.set_enabled(self.session, True, platform="claude", native_context=context)
        self.assertEqual(self.engine.path.read_bytes(), before)
        common = [sys.executable, str(SCRIPT), "--root", str(self.root), "--user", "actual-user",
                  "--session", self.session, "--platform", "codex"]
        completed = subprocess.run(common + ["--native-context", json.dumps(context), "on"],
                                   capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        item = json.loads(completed.stdout)["orchestrator_suggestion"]["recommendations"][0]
        self.assertEqual(item["model_id"], "current")
        self.assertFalse(item["applied"])
        self.assertEqual(self.engine.path.read_bytes(), before)
        invalid = subprocess.run(common + ["--native-context", "{", "on"], capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 1)
        self.assertEqual(self.engine.path.read_bytes(), before)

    def test_v3_adoption_preserves_executor_window_and_resets_old_advisor(self):
        outstanding = write_policy_two_fixture(self.engine, self.session)
        before = self.events()
        old_advisor = next(row["data"] for row in before if row["run_id"] == "advisor-3")
        rows = self.events()
        self.engine._append(rows, "policy_adoption", {"from_policy_version": "optimal-ultra-ladder-v2", "to_policy_version": "optimal-ultra-ladder-v3"})
        self.write_events(rows)
        status = self.engine.status(self.session)
        self.assertEqual(status["policy_version"], "optimal-ultra-ladder-v3")
        self.assertEqual(self.events()[:len(before)], before)
        self.assertEqual(len(status["tracks"]), 1)
        self.assertEqual((status["tracks"][0]["role"], status["tracks"][0]["epoch"],
                          status["tracks"][0]["eligible_count"]), ("executor", "executor-v1", 3))
        self.assertIn("policy_changed", self.assess(old_advisor)["exclusions"])
        self.assertTrue(self.assess(outstanding)["eligible"])
        launched = self.engine.prepare(self.session, "codex", "executor", "medium",
                                        {"terra": "terra-old", "sol": "sol-old"}, list(range(7)))
        self.assertEqual(launched["epoch"], "executor-v1")
        self.assertEqual(launched["policy_version"], "optimal-ultra-ladder-v4")
        self.assertEqual(self.assess(launched)["transition"]["step"], 2)
        advisor = self.engine.prepare(self.session, "codex", "advisor",
                                      models={"sol": "sol-old", "astra": "astra-new"},
                                      available_steps=[0, 1, 2], advice_level="high")
        self.assertEqual((advisor["step"], advisor["context_floor"]), (1, 1))
        self.assertNotEqual(advisor["epoch"], "advisor-v1")

    def test_assessment_uses_its_run_floor_despite_later_context_relaxation(self):
        self.enable()
        args = dict(session=self.session, platform="codex", role="advisor",
                    models={"sol": "sol-v1", "astra": "astra-v1"}, available_steps=[0, 1, 2])
        for _ in range(4):
            self.assess(self.engine.prepare(**args, advice_level="high"), score=5)
        high = self.engine.prepare(**args, advice_level="high")
        medium = self.engine.prepare(**args, advice_level="medium")
        self.assertEqual(high["epoch"], medium["epoch"])
        self.assertIsNone(self.assess(high, score=5)["transition"])
        self.assertEqual(self.engine.status(self.session)["tracks"][0]["step"], 1)
        descended = self.engine.prepare(**args, advice_level="medium")
        self.assertEqual(descended["step"], 0)
        self.assertNotEqual(descended["epoch"], high["epoch"])

    def test_advisor_purpose_gate_uses_shared_policy_and_keeps_low_planning_baseline(self):
        self.enable()
        args = dict(session=self.session, platform="codex", role="advisor",
                    models={"sol": "sol-v1", "astra": "astra-v1"}, available_steps=[0, 1, 2])
        with self.assertRaisesRegex(ValueError, "consult"):
            self.engine.prepare(**args, purpose="execution", complexity="low", needed=True)
        planning = self.engine.prepare(**args, purpose="planning", complexity="low")
        self.assertEqual((planning["advice_level"], planning["context_floor"]), ("medium", 0))
        self.assertTrue(planning["consultation"]["required"])

    def test_replay_rejects_corrupt_advisor_consultation_before_read_or_prepare(self):
        self.enable()
        args = dict(session=self.session, platform="codex", role="advisor",
                    models={"sol": "sol-v1", "astra": "astra-v1"}, available_steps=[0, 1, 2])
        run = self.engine.prepare(**args, purpose="planning", complexity="low")
        original = self.engine.path.read_bytes()
        cases = {"purpose": "execution", "complexity": "super_high", "needed": "yes",
                 "required": False, "allowed": False, "consult": False, "advice_level": "high",
                 "starting_step": False, "family": "astra", "effort": "max"}
        high = dict(advisor_context("codex", "super_high", "planning", False),
                    purpose="planning", complexity="super_high", needed=False)
        disallowed = dict(advisor_context("codex", "low", "execution", True),
                          purpose="execution", complexity="low", needed=True)
        for case, value in list(cases.items()) + [("insufficient_floor", high), ("disallowed", disallowed), ("not_object", [])]:
            for operation in ("status", "prepare"):
                with self.subTest(case=case, operation=operation):
                    self.engine.path.write_bytes(original)
                    rows = self.events()
                    launch = next(row for row in rows if row["event_type"] == "launch"
                                  and row["data"]["run_id"] == run["run_id"])
                    if case in ("insufficient_floor", "disallowed", "not_object"):
                        launch["data"]["consultation"] = value
                    else:
                        launch["data"]["consultation"][case] = value
                    self.write_events(rows)
                    corrupted = self.engine.path.read_bytes()
                    with self.assertRaises(ValueError):
                        if operation == "status":
                            self.engine.status(self.session)
                        else:
                            self.engine.prepare(**args)
                    self.assertEqual(self.engine.path.read_bytes(), corrupted)

    def test_replay_accepts_explicitly_raised_advisor_level_with_consultation(self):
        self.enable()
        args = dict(session=self.session, platform="codex", role="advisor",
                    models={"sol": "sol-v1", "astra": "astra-v1"}, available_steps=[0, 1, 2])
        run = self.engine.prepare(**args, purpose="planning", complexity="low", advice_level="high")
        self.assertEqual(run["consultation"]["starting_step"], 0)
        self.assertEqual(run["context_floor"], 1)
        self.assertEqual(Engine(self.root, "actual-user").status(self.session)["tracks"][0]["step"], 1)

    def test_replay_rejects_noop_advisor_context_event(self):
        self.enable()
        run = self.engine.prepare(self.session, "codex", "advisor",
                                  models={"sol": "sol-v1", "astra": "astra-v1"},
                                  available_steps=[0, 1, 2])
        rows = self.events()
        self.engine._append(rows, "advisor_context", dict(platform="codex", role="advisor",
                            tier=None, epoch=run["epoch"], advice_level="medium", context_floor=0))
        self.write_events(rows)
        corrupted = self.engine.path.read_bytes()
        for operation in ("status", "disable"):
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                if operation == "status":
                    self.engine.status(self.session)
                else:
                    self.engine.set_enabled(self.session, False)
            self.assertEqual(self.engine.path.read_bytes(), corrupted)

    def test_replay_rejects_advisor_context_before_v3(self):
        write_policy_two_fixture(self.engine, self.session)
        rows = self.events()
        self.engine._append(rows, "advisor_context", dict(platform="codex", role="advisor",
                            tier=None, epoch="advisor-v1", advice_level="medium", context_floor=0))
        self.write_events(rows)
        corrupted = self.engine.path.read_bytes()
        for operation in ("status", "disable"):
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                if operation == "status":
                    self.engine.status(self.session)
                else:
                    self.engine.set_enabled(self.session, False)
            self.assertEqual(self.engine.path.read_bytes(), corrupted)

    def test_medium_receipt_can_descend_after_high_prepare_and_stale_high_cannot_move(self):
        self.enable()
        args = dict(session=self.session, platform="codex", role="advisor",
                    models={"sol": "sol-v1", "astra": "astra-v1"}, available_steps=[0, 1, 2])
        self.engine.prepare(**args, advice_level="high")
        for level in ("medium", "high", "medium", "high"):
            self.assess(self.engine.prepare(**args, advice_level=level), score=5)
        medium = self.engine.prepare(**args, advice_level="medium")
        high = self.engine.prepare(**args, advice_level="high")
        self.assertEqual(medium["epoch"], high["epoch"])
        descended = self.assess(medium, score=5)["transition"]
        self.assertEqual(descended["step"], 0)
        self.assertIsNone(self.assess(high, score=0)["transition"])
        self.assertEqual(self.engine.status(self.session)["tracks"][0]["epoch"], descended["epoch"])
        raised = self.engine.prepare(**args, advice_level="high")
        self.assertEqual(raised["step"], 1)
        self.assertNotEqual(raised["epoch"], descended["epoch"])

    def test_invalid_context_inputs_fail_before_writes_and_cannot_lower_required_floor(self):
        for kwargs in ({"platform": "unknown"}, {"complexity": "unknown"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.engine.set_enabled(self.session, True, **kwargs)
            self.assertFalse(self.engine.path.exists())
        self.enable()
        before = self.engine.path.read_bytes()
        args = dict(session=self.session, platform="codex", role="advisor", purpose="planning",
                    complexity="high", models={"sol": "sol-v1", "astra": "astra-v1"},
                    available_steps=[0, 1, 2])
        for invalid in ([], {}, 1, "invalid", "medium"):
            with self.subTest(advice_level=invalid), self.assertRaises(ValueError):
                self.engine.prepare(**args, advice_level=invalid)
            self.assertEqual(self.engine.path.read_bytes(), before)
        with self.assertRaises(ValueError):
            self.engine.prepare(**dict(args, complexity="super_high"), advice_level="high")
        self.assertEqual(self.engine.path.read_bytes(), before)

    def test_replay_rejects_numeric_floor_conflicting_with_advice_level(self):
        self.enable()
        self.engine.prepare(self.session, "codex", "advisor", models={"sol": "sol-v1"},
                            available_steps=[0, 1], advice_level="high")
        rows = self.events()
        rows[-1]["data"]["context_floor"] = 0
        self.write_events(rows)
        before = self.engine.path.read_bytes()
        with self.assertRaises(ValueError):
            self.engine.status(self.session)
        self.assertEqual(self.engine.path.read_bytes(), before)

    def test_advisor_task_context_requires_purpose_and_boolean_needed(self):
        self.enable()
        before = self.engine.path.read_bytes()
        args = dict(session=self.session, platform="codex", role="advisor",
                    models={"sol": "sol-v1", "astra": "astra-v1"}, available_steps=[0, 1, 2])
        for context in ({"complexity": "low", "needed": True}, {"complexity": "high"},
                        {"needed": True}, {"needed": "yes"}, {"needed": 0}):
            with self.subTest(context=context), self.assertRaises(ValueError):
                self.engine.prepare(**args, **context)
            self.assertEqual(self.engine.path.read_bytes(), before)

    def test_policy_version_is_explicit(self):
        self.enable()
        self.assertEqual(self.events()[0]["data"]["policy_version"], "optimal-ultra-ladder-v4")

    def test_cli_json_success_and_clean_errors(self):
        common = [sys.executable, str(SCRIPT), "--root", str(self.root),
                  "--user", "actual-user", "--session", self.session]
        enabled = subprocess.run(common + ["--platform", "codex", "--complexity", "low", "on"],
                                 capture_output=True, text=True)
        self.assertEqual(enabled.returncode, 0, enabled.stderr)
        self.assertTrue(json.loads(enabled.stdout)["enabled"])
        self.assertEqual(json.loads(enabled.stdout)["orchestrator_suggestion"]["recommendations"][0]["effort"],
                         "medium")
        request = self.root / "request.json"
        request.write_text(json.dumps(dict(platform="codex", role="executor", tier="low",
                                           models=MODELS, available_steps=list(range(7)))))
        launched = subprocess.run(common + ["prepare", str(request)], capture_output=True, text=True)
        self.assertEqual(launched.returncode, 0, launched.stderr)
        self.assertEqual(json.loads(launched.stdout)["model_id"], "terra-v1")
        request.write_text("{")
        failed = subprocess.run(common + ["prepare", str(request)], capture_output=True, text=True)
        self.assertEqual(failed.returncode, 1)
        self.assertEqual(len(failed.stderr.splitlines()), 1)
        self.assertNotIn("Traceback", failed.stderr)
        self.assertEqual(failed.stdout, "")


if __name__ == "__main__":
    unittest.main()
