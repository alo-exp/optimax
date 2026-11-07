"""Observable policy and read-only CLI contracts for the ladder calculator."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'skills/optimax'
SPEC = importlib.util.spec_from_file_location("ladder", ROOT / "scripts" / "ladder.py")
ladder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ladder)


DEFAULT_TIER = object()


def request(platform="codex", role="executor", tier=DEFAULT_TIER, step=0, scores=()):
    if tier is DEFAULT_TIER:
        tier = None if role == "advisor" else "low"
    track = dict(platform=platform, role=role, tier=tier, step=step,
                 model_id="actual-model-v1", epoch="initial")
    sizes = {("claude", "executor"): 6, ("codex", "executor"): 7,
             ("claude", "advisor"): 3, ("codex", "advisor"): 3}
    records = [dict(track, run_id=f"run-{i}", timestamp=f"2026-11-01T00:00:0{i}+00:00",
                    score=score, verified=True) for i, score in enumerate(scores)]
    return dict(track=track, available_steps=list(range(sizes[(platform, role)])),
                assessments=records)


class LadderTests(unittest.TestCase):
    def test_advisor_v3_ceiling_and_contextual_floors(self):
        expected = {"claude": [("opus", "medium"), ("opus", "high"), ("opus", "xhigh")],
                    "codex": [("sol", "xhigh"), ("sol", "max"), ("astra", "max")]}
        for platform, rungs in expected.items():
            for level, floor in (("medium", 0), ("high", 1), ("super_high", 2)):
                base = request(platform=platform, role="advisor")
                base.update(available_steps=[0, 1, 2], advice_level=level)
                result = ladder.recommend(base)
                self.assertEqual(result["selected_step"], floor)
                self.assertEqual((result["selected_family"], result["selected_effort"]), rungs[floor])

    def test_lower_advisor_context_alone_does_not_demote_but_perfect_window_can(self):
        base = request(role="advisor", step=2, scores=[4, 5])
        base.update(available_steps=[0, 1, 2], advice_level="medium")
        self.assertEqual(ladder.recommend(base)["selected_step"], 2)
        base = request(role="advisor", step=2, scores=[5] * 5)
        base.update(available_steps=[0, 1, 2], advice_level="high")
        self.assertEqual(ladder.recommend(base)["selected_step"], 1)
        base["advice_level"] = "super_high"
        self.assertEqual(ladder.recommend(base)["selected_step"], 2)

    def test_latest_executor_ladders_are_exact(self):
        expected = {
            "claude": [("haiku", "high"), ("haiku", "xhigh"), ("haiku", "max"),
                       ("sonnet", "high"), ("opus", "medium"), ("opus", "high")],
            "codex": [("terra", "low"), ("terra", "medium"), ("terra", "high"),
                      ("sol", "medium"), ("sol", "high"), ("sol", "xhigh"), ("sol", "max")],
        }
        for platform, rungs in expected.items():
            for step, pair in enumerate(rungs):
                base = request(platform=platform, step=step)
                base["available_steps"] = list(range(len(rungs)))
                with self.subTest(platform=platform, step=step):
                    result = ladder.recommend(base)
                    self.assertEqual((result["selected_family"], result["selected_effort"]), pair)

    def test_latest_normal_starts_and_preserved_business_exception_floors(self):
        for platform, floors in (("claude", [0, 2, 3, 4]), ("codex", [0, 1, 2, 5])):
            for tier, floor in zip(("low", "medium", "high", "business_doc"), floors):
                base = request(platform=platform, tier=tier, step=floor, scores=[5] * 5)
                base["available_steps"] = list(range(6 if platform == "claude" else 7))
                with self.subTest(platform=platform, tier=tier):
                    self.assertEqual(ladder.recommend(base)["selected_step"], floor)

    def test_policy_registry_preserves_old_ordinals_and_rejects_unknown_policy(self):
        previous = {
            "claude": [("haiku", "xhigh"), ("haiku", "max"), ("sonnet", "high"),
                       ("sonnet", "xhigh"), ("opus", "low"), ("opus", "medium")],
            "codex": [("luna", "max"), ("sol", "high"), ("sol", "xhigh"), ("sol", "max")],
        }
        for platform, rungs in previous.items():
            for step, expected in enumerate(rungs):
                base = request(platform=platform, step=step)
                base.update(policy_version="optimal-ultra-ladder-v1",
                            available_steps=list(range(len(rungs))))
                result = ladder.recommend(base)
                self.assertEqual((result["selected_family"], result["selected_effort"]), expected)
        for value in (None, "unknown", 2, {}):
            with self.subTest(policy=value), self.assertRaises(ValueError):
                ladder.recommend(request() | {"policy_version": value})

    def test_four_results_do_not_move(self):
        result = ladder.recommend(request(scores=[0, 0, 0, 0]))
        self.assertEqual(result["selected_step"], 0)
        self.assertEqual(result["eligible_count"], 4)
        self.assertEqual(result["average"], None)
        self.assertEqual(result["reason"], "insufficient_evidence")
        self.assertFalse(result["reset_required"])

    def test_five_average_44_escalates(self):
        result = ladder.recommend(request(scores=[4, 4, 4, 5, 5]))
        self.assertEqual(result["selected_step"], 1)
        self.assertEqual(result["average"], 4.4)
        self.assertEqual(result["reason"], "low_performance")
        self.assertTrue(result["reset_required"])

    def test_average_46_stays(self):
        result = ladder.recommend(request(scores=[4, 4, 5, 5, 5]))
        self.assertEqual(result["selected_step"], 0)
        self.assertEqual(result["reason"], "performance_stable")
        self.assertFalse(result["reset_required"])

    def test_five_perfect_moves_down(self):
        result = ladder.recommend(request(step=2, scores=[5] * 5))
        self.assertEqual(result["selected_step"], 1)
        self.assertEqual(result["reason"], "perfect_performance")
        self.assertTrue(result["reset_required"])

    def test_perfect_at_floor_stays(self):
        result = ladder.recommend(request(tier="high", step=2, scores=[5] * 5))
        self.assertEqual(result["selected_step"], 2)
        self.assertEqual(result["reason"], "floor_reached")

    def test_bad_at_ceiling_stays(self):
        result = ladder.recommend(request(step=6, scores=[0] * 5))
        self.assertEqual(result["selected_step"], 6)
        self.assertEqual(result["reason"], "ceiling_reached")
        self.assertFalse(result["reset_required"])

    def test_every_ladder_mapping(self):
        ladders = {
            ("claude", "executor"): [("haiku", "high"), ("haiku", "xhigh"),
                ("haiku", "max"), ("sonnet", "high"), ("opus", "medium"), ("opus", "high")],
            ("codex", "executor"): [("terra", "low"), ("terra", "medium"), ("terra", "high"),
                ("sol", "medium"), ("sol", "high"), ("sol", "xhigh"), ("sol", "max")],
            ("claude", "advisor"): [("opus", "medium"), ("opus", "high"), ("opus", "xhigh")],
            ("codex", "advisor"): [("sol", "xhigh"), ("sol", "max"), ("astra", "max")],
        }
        for (platform, role), steps in ladders.items():
            for step, expected in enumerate(steps):
                with self.subTest(platform=platform, role=role, step=step):
                    result = ladder.recommend(request(platform, role, step=step))
                    self.assertEqual((result["selected_family"], result["selected_effort"]), expected)

    def test_executor_floors_and_business_document_floor(self):
        for platform, floors in [("claude", [0, 2, 3, 4]), ("codex", [0, 1, 2, 5])]:
            for tier, floor in zip(["low", "medium", "high", "business_doc"], floors):
                with self.subTest(platform=platform, tier=tier):
                    result = ladder.recommend(request(platform, tier=tier, step=floor, scores=[5] * 5))
                    self.assertEqual(result["selected_step"], floor)
                    if floor:
                        with self.assertRaises(ValueError):
                            ladder.recommend(request(platform, tier=tier, step=floor - 1))

    def test_advisor_has_one_track_without_complexity_and_rejects_supplied_tier(self):
        for platform in ["claude", "codex"]:
            self.assertEqual(ladder.recommend(request(platform, "advisor", None, 1, [5] * 5))["selected_step"], 0)
            for tier in ["low", "medium", "high", "business_doc", "", 1]:
                with self.subTest(platform=platform, tier=tier), self.assertRaises(ValueError):
                    ladder.recommend(request(platform, "advisor", tier))

    def test_exact_track_version_and_epoch_isolation(self):
        base = request(scores=[0] * 4)
        variants = dict(platform="claude", role="advisor", tier="medium", step=1,
                        model_id="actual-model-v2", epoch="previous")
        for key, value in variants.items():
            item = dict(base["assessments"][0], run_id=key)
            item[key] = value
            if key == "role":
                item["tier"] = None
            base["assessments"].append(item)
        result = ladder.recommend(base)
        self.assertEqual(result["eligible_count"], 4)
        self.assertEqual(result["excluded_count"], 6)
        self.assertEqual(result["selected_step"], 0)

    def test_latest_five_by_timestamp_not_array_order(self):
        base = request(scores=[0, 5, 5, 5, 5, 5])
        base["assessments"] = list(reversed(base["assessments"]))
        result = ladder.recommend(base)
        self.assertEqual(result["window_run_ids"], ["run-1", "run-2", "run-3", "run-4", "run-5"])
        self.assertEqual(result["eligible_count"], 6)
        self.assertEqual(result["average"], 5)

    def test_timestamp_offsets_normalized_and_ties_preserve_order(self):
        base = request(scores=[0, 1, 2, 3, 4, 5])
        base["assessments"][0]["timestamp"] = "2026-11-01T01:00:00+01:00"
        for item in base["assessments"][1:]:
            item["timestamp"] = "2026-11-01T00:00:00Z"
        result = ladder.recommend(base)
        self.assertEqual(result["window_run_ids"], ["run-1", "run-2", "run-3", "run-4", "run-5"])

    def test_unverified_and_each_missing_attribution_excluded(self):
        base = request(scores=[5])
        fields = ["run_id", "timestamp", "platform", "role", "tier", "step", "model_id", "epoch", "score", "verified"]
        for field in fields:
            item = dict(base["assessments"][0], run_id="missing-" + field)
            del item[field]
            base["assessments"].append(item)
        base["assessments"].append(dict(base["assessments"][0], run_id="unverified", verified=False))
        result = ladder.recommend(base)
        self.assertEqual(result["eligible_count"], 1)
        self.assertEqual(result["excluded_count"], 11)

    def test_incomplete_advisor_missing_role_is_excluded_without_inventing_tier(self):
        base = request(role="advisor", scores=[5])
        record = base["assessments"][0]
        del record["role"]
        result = ladder.recommend(base)
        self.assertEqual(result["eligible_count"], 0)
        self.assertEqual(result["excluded_count"], 1)
        self.assertEqual(result["selected_step"], 0)

    def test_explicit_executor_null_tier_remains_invalid(self):
        with self.assertRaises(ValueError):
            ladder.recommend(request(tier=None))

    def test_duplicate_run_ids_rejected_even_on_other_track(self):
        base = request(scores=[5])
        base["assessments"].append(dict(base["assessments"][0], epoch="different"))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            ladder.recommend(base)

    def test_invalid_scores_rejected(self):
        for value in [True, False, -1, 6, 4.0, "5", None]:
            with self.subTest(value=value):
                base = request(scores=[value])
                with self.assertRaises(ValueError):
                    ladder.recommend(base)

    def test_invalid_timestamps_rejected(self):
        for value in ["2026-11-01", "2026-11-01T00:00:00", "not-a-date", None, 123]:
            with self.subTest(value=value):
                base = request(scores=[5])
                base["assessments"][0]["timestamp"] = value
                with self.assertRaises(ValueError):
                    ladder.recommend(base)

    def test_malformed_excluded_record_still_rejected(self):
        base = request(scores=[True])
        base["assessments"][0]["epoch"] = "other"
        with self.assertRaises(ValueError):
            ladder.recommend(base)

    def test_invalid_record_types_and_indices_rejected(self):
        for field, value in [("verified", 1), ("step", True), ("step", -1), ("step", 7),
                             ("platform", "other"), ("role", "other"), ("tier", "other"),
                             ("model_id", ""), ("epoch", ""), ("run_id", 1)]:
            with self.subTest(field=field, value=value):
                base = request(scores=[5])
                base["assessments"][0][field] = value
                with self.assertRaises(ValueError):
                    ladder.recommend(base)
        for record in [None, 1, []]:
            base = request()
            base["assessments"].append(record)
            with self.assertRaises(ValueError):
                ladder.recommend(base)

    def test_invalid_request_shapes_and_track_fields_rejected(self):
        for base in [None, [], {}, {"track": {}}, request() | {"assessments": {}},
                     request() | {"track": None}]:
            with self.subTest(base=base), self.assertRaises(ValueError):
                ladder.recommend(base)
        for field, value in [("platform", "other"), ("role", "other"), ("tier", "other"),
                             ("step", True), ("step", -1), ("step", 7),
                             ("model_id", ""), ("epoch", None)]:
            base = request()
            base["track"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                ladder.recommend(base)
        for field in request()["track"]:
            base = request()
            del base["track"][field]
            with self.subTest(missing=field), self.assertRaises(ValueError):
                ladder.recommend(base)

    def test_invalid_availability_rejected(self):
        for available in [None, [], [0, 0], [True], [0.0], [-1], [7], "0"]:
            base = request()
            base["available_steps"] = available
            with self.subTest(available=available), self.assertRaises(ValueError):
                ladder.recommend(base)
        base = request()
        del base["available_steps"]
        with self.assertRaises(ValueError):
            ladder.recommend(base)

    def test_availability_skip_up_and_down(self):
        base = request(scores=[0] * 5)
        base["available_steps"] = [3, 0]
        self.assertEqual(ladder.recommend(base)["selected_step"], 3)
        base = request(step=3, scores=[5] * 5)
        base["available_steps"] = [3, 0]
        self.assertEqual(ladder.recommend(base)["selected_step"], 0)

    def test_capability_fallback_precedes_evidence(self):
        base = request(step=1, scores=[5] * 5)
        base["available_steps"] = [0, 3]
        result = ladder.recommend(base)
        self.assertEqual(result["selected_step"], 3)
        self.assertEqual(result["reason"], "capability_fallback")
        self.assertTrue(result["reset_required"])

    def test_no_supported_higher_fallback_rejected(self):
        base = request(step=2)
        base["available_steps"] = [0, 1]
        with self.assertRaises(ValueError):
            ladder.recommend(base)

    def test_availability_below_floor_does_not_allow_downshift(self):
        base = request(tier="medium", step=2, scores=[5] * 5)
        base["available_steps"] = [0, 2]
        result = ladder.recommend(base)
        self.assertEqual(result["selected_step"], 2)
        self.assertEqual(result["reason"], "floor_reached")

    def test_no_input_mutation_and_repeatable_output(self):
        base = request(scores=[4] * 5)
        original = copy.deepcopy(base)
        first = ladder.recommend(base)
        self.assertEqual(base, original)
        self.assertEqual(ladder.recommend(base), first)

    def test_cli_json_success_is_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            path.write_text(json.dumps(request(scores=[4] * 5)), encoding="utf-8")
            before = path.read_bytes()
            result = subprocess.run([sys.executable, str(ROOT / "scripts" / "ladder.py"), str(path)],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["selected_step"], 1)
            self.assertEqual(result.stderr, "")
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_cli_compact_failure(self):
        for content in ["{", "{}", json.dumps(request(scores=[True]))]:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "bad.json"
                path.write_text(content, encoding="utf-8")
                result = subprocess.run([sys.executable, str(ROOT / "scripts" / "ladder.py"), str(path)],
                                        capture_output=True, text=True, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertEqual(len(result.stderr.strip().splitlines()), 1)
                self.assertNotIn("Traceback", result.stderr)

    def test_cli_missing_file_and_argument_fail_cleanly(self):
        for arguments in [[], ["/nonexistent/ladder-request.json"]]:
            with self.subTest(arguments=arguments):
                result = subprocess.run([sys.executable, str(ROOT / "scripts" / "ladder.py"), *arguments],
                                        capture_output=True, text=True, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertEqual(len(result.stderr.strip().splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
