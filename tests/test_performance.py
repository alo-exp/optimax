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

MODELS = {"terra": "terra-v1", "sol": "sol-v1"}
CLAUDE_MODELS = {"haiku": "haiku-v1", "sonnet": "sonnet-v1", "opus": "opus-v1"}
SCRIPT = Path(__file__).resolve().parents[1] / "skills/optimax/scripts" / "performance.py"


def parallel_prepare(arguments):
    root, user, session = arguments
    return Engine(root, user).prepare(session, "codex", "executor", "low", MODELS, list(range(7)))


def parallel_assess(arguments):
    root, run = arguments
    return Engine(root, "actual-user").assess(
        run["run_id"], 4, run["model_id"], run["effort"], "exec-" + run["run_id"])


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

    def test_default_off_read_only_and_explicit_session_enable(self):
        self.assertFalse(self.engine.status(self.session)["enabled"])
        self.assertFalse(self.engine.path.exists())
        with self.assertRaisesRegex(ValueError, "disabled"):
            self.prepare()
        self.enable()
        self.assertTrue(Engine(self.root, "actual-user").status(self.session)["enabled"])
        self.assertFalse(self.engine.status("other-session")["enabled"])

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
                                          "exec-" + run["run_id"]), result)
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
                                      "exec-" + run["run_id"]), result)

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

    def test_sequential_v1_v2_v3_adoption_preserves_history_and_retires_changed_roles(self):
        old_executor = write_policy_one_fixture(self.engine, self.session)
        before = self.engine.path.read_bytes()
        historical = self.events()
        status = self.engine.status(self.session)
        self.assertEqual(status["policy_version"], "optimal-ultra-ladder-v1")
        self.assertEqual(self.engine.path.read_bytes(), before)
        adopted = self.engine.adopt_policy()
        self.assertTrue(adopted["changed"])
        self.assertEqual(adopted["policy_version"], "optimal-ultra-ladder-v3")
        self.assertEqual([row["data"]["to_policy_version"] for row in self.events()
                          if row["event_type"] == "policy_adoption"],
                         ["optimal-ultra-ladder-v2", "optimal-ultra-ladder-v3"])
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
        self.assertEqual(sum(row["event_type"] == "policy_adoption" for row in self.events()), 2)
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
                         {"changed": True, "policy_version": "optimal-ultra-ladder-v3"})
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
        self.engine.adopt_policy()
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
        self.assertEqual(launched["policy_version"], "optimal-ultra-ladder-v3")
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
        self.assertEqual(self.events()[0]["data"]["policy_version"], "optimal-ultra-ladder-v3")

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
