import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from skills.optimax.scripts.work_breakdown import readiness


def task(id, deps=(), paths=(), resources=()):
    return dict(id=id, outcome="deliver", acceptance="verify",
                dependencies=list(deps), complexity="low",
                write_paths=list(paths), resources=list(resources))


class ReadinessTests(unittest.TestCase):
    def test_occupancy_must_be_known_before_selecting_ready_work(self):
        plan = [task("native"), task("direct")]
        with self.assertRaisesRegex(ValueError, "other_inflight"):
            readiness(plan, [], ["native"], 2)
        with self.assertRaisesRegex(ValueError, "other_inflight"):
            readiness(plan, [], ["native"], 2, None)
        zero = readiness(plan, [], ["native"], 2, 0)
        self.assertEqual(zero["ready"], ["direct"])
        self.assertEqual(zero["used_capacity"], 2)
        occupied = readiness(plan, [], ["native"], 2, 1)
        self.assertEqual(occupied["ready"], [])
        self.assertEqual(occupied["status"]["direct"], "capacity")
        self.assertEqual(occupied["used_capacity"], 2)

    def test_branching_acceptance_and_running_capacity(self):
        plan = [task("a"), task("b"), task("next", ["a"])]
        self.assertEqual(readiness(plan, [], [], 2, 0)["ready"], ["a", "b"])
        self.assertEqual(readiness(plan, [], ["b"], 2, 0)["ready"], ["a"])
        result = readiness(plan, ["a"], ["b"], 2, 0)
        self.assertEqual(result["ready"], ["next"])
        self.assertEqual(result["used_capacity"], 2)
        self.assertEqual(readiness(plan, [], ["b"], 2, 0)["status"]["next"], "dependencies")
        self.assertEqual(readiness(plan, [], [], 2, 2)["ready"], [])

    def test_ownership_and_resources(self):
        plan = [task("a", paths=["src"]), task("b", paths=["src/file"]),
                task("c", paths=["other"], resources=["db"]),
                task("d", paths=["elsewhere"], resources=["db"])]
        result = readiness(plan, [], [], 4, 0)
        self.assertEqual(result["ready"], ["a", "c"])
        self.assertEqual(result["status"]["b"], "ownership")
        self.assertEqual(result["status"]["d"], "resources")
        self.assertEqual(readiness([task("a", paths=["src/a"]), task("b", paths=["src/ab"])], [], [], 2, 0)["ready"], ["a", "b"])
        self.assertEqual(readiness(plan, [], ["a"], 4, 0)["status"]["b"], "ownership")

    def test_invalid_inputs(self):
        invalid = [
            ([task("a"), task("a")], [], [], 2, 0),
            ([task("a", ["missing"])], [], [], 2, 0),
            ([task("a", ["b"]), task("b", ["a"])], [], [], 2, 0),
            ([task("a")], ["a"], ["a"], 2, 0),
            ([task("a")], ["missing"], [], 2, 0),
            ([task("a")], [], ["missing"], 2, 0),
            ([task("a")], [], ["a"], 0, 0),
            ([task("a")], [], [], -1, 0),
            ([task("a")], [], [], 1, 2),
            ([dict(task("a"), complexity="huge")], [], [], 1, 0),
            ([dict(task("a"), outcome=" ")], [], [], 1, 0),
            ([dict(task("a"), dependencies="a")], [], [], 1, 0),
            ([dict(task("a"), write_paths=[""])], [], [], 1, 0),
            ([dict(task("a"), resources=[1])], [], [], 1, 0),
            ([dict(task("a"), acceptance=None)], [], [], 1, 0),
        ]
        for args in invalid:
            with self.subTest(args=args), self.assertRaises(ValueError):
                readiness(*args)

    def test_empty_and_no_mutation(self):
        self.assertEqual(readiness([], [], [], 0, 0), {"ready": [], "status": {}, "used_capacity": 0})
        plan = [task("a"), task("b", ["a"])]
        accepted, running = ["a"], []
        before = copy.deepcopy((plan, accepted, running))
        readiness(plan, accepted, running, 2, 0)
        self.assertEqual((plan, accepted, running), before)

    def test_deep_chain_and_cycle(self):
        plan = [task(str(i), [str(i + 1)] if i < 1199 else [])
                for i in range(1200)]
        result = readiness(plan, [], [], 1, 0)
        self.assertEqual(result["ready"], ["1199"])
        self.assertEqual(result["status"]["0"], "dependencies")
        plan[-1]["dependencies"] = ["0"]
        with self.assertRaisesRegex(ValueError, "cycle"):
            readiness(plan, [], [], 1, 0)


class ExecutionCheckpointTests(unittest.TestCase):
    def checkpoint(self, activity="code", owner="root", assignment=None, **extra):
        item = task("work")
        item["execution"] = dict(activity=activity, proposed_owner=owner, **extra)
        if assignment is not None:
            item["execution"]["assignment"] = assignment
        result = readiness([item], [], [], 1, 0, enabled=True)
        return result.get("execution_checkpoints", {}).get("work", {})

    def test_advisor_only_does_not_authorize_root_substantive_work(self):
        advisor = dict(assignment_id="advisor-1", role="advisor", stage="planning", host_returned=True)
        for activity in ("code", "test_authoring", "test_work", "research",
                         "documentation", "release_preparation", "semantic_integration"):
            with self.subTest(activity=activity):
                result = self.checkpoint(activity, assignment=advisor)
                self.assertEqual(result.get("next_action"), "dispatch_executor")
                self.assertIs(result.get("execution_allowed"), False)
                self.assertIs(result.get("learning_eligible"), False)

    def test_actual_executor_snapshot_establishes_ownership_without_provider_receipt(self):
        assignment = dict(assignment_id="executor-1", role="executor", stage="execution", host_returned=True)
        result = self.checkpoint(owner="executor", assignment=assignment)
        self.assertIs(result.get("execution_allowed"), True)
        self.assertEqual(result.get("next_action"), "continue_executor")
        self.assertEqual(result.get("ownership_basis"), "declared_host_snapshot")
        self.assertIs(result.get("provider_verified"), False)
        self.assertIs(result.get("learning_eligible"), False)
        for change in (dict(role="advisor"), dict(stage="planning"), dict(host_returned=False)):
            with self.subTest(change=change):
                candidate = dict(assignment, **change)
                self.assertEqual(self.checkpoint(owner="executor", assignment=candidate).get("next_action"), "dispatch_executor")

    def test_root_coordination_inspection_verification_and_acceptance_are_allowed(self):
        for activity in ("coordination", "source_inspection", "independent_verification", "acceptance"):
            with self.subTest(activity=activity):
                result = self.checkpoint(activity)
                self.assertIs(result.get("execution_allowed"), True)
                self.assertEqual(result.get("next_action"), "root_permitted")

    def test_blocked_readiness_never_grants_root_fallback(self):
        for capacity, deps, accepted in ((0, [], []), (1, ["dep"], [])):
            with self.subTest(capacity=capacity, deps=deps):
                item = task("work", deps)
                item["execution"] = dict(activity="code", proposed_owner="root")
                plan = ([task("dep")] if deps else []) + [item]
                result = readiness(plan, accepted, [], capacity, 0, enabled=True)
                check = result.get("execution_checkpoints", {}).get("work", {})
                self.assertIs(check.get("execution_allowed"), False)
                self.assertEqual(check.get("next_action"), "wait_for_" + result["status"]["work"])

    def test_explicit_user_exception_requires_evidence_scope_and_authority(self):
        exception = dict(evidence="User explicitly permits root patch", scope="work",
                         authority="new_explicit_user_instruction")
        result = self.checkpoint(user_exception=exception)
        self.assertIs(result.get("execution_allowed"), True)
        self.assertEqual(result.get("next_action"), "explicit_user_exception")
        for bad in ({}, dict(exception, scope="other"), dict(exception, evidence="")):
            with self.subTest(exception=bad):
                with self.assertRaises(ValueError):
                    self.checkpoint(user_exception=bad)

    def test_running_executor_and_late_root_deviation_preserve_work_without_duplicate(self):
        assignment = dict(assignment_id="native-1", role="executor", stage="execution", host_returned=True)
        item = task("work")
        item["execution"] = dict(activity="code", proposed_owner="executor", assignment=assignment)
        result = readiness([item], [], ["work"], 1, 0, enabled=True)
        self.assertEqual(result["ready"], [])
        self.assertEqual(result.get("execution_checkpoints", {}).get("work", {}).get("next_action"), "continue_executor")
        late = self.checkpoint(root_started=True, root_start_authorized=False)
        self.assertIs(late.get("deviation"), True)
        self.assertEqual(late.get("next_action"), "delegate_remaining")
        self.assertIs(late.get("preserve_existing_work"), True)

    def test_off_defers_to_host_policy_and_inputs_are_not_mutated(self):
        item = task("work")
        item["execution"] = dict(activity="code", proposed_owner="root")
        before = copy.deepcopy(item)
        result = readiness([item], [], [], 1, 0, enabled=False)
        check = result.get("execution_checkpoints", {}).get("work", {})
        self.assertEqual(check.get("next_action"), "defer_to_host_policy")
        self.assertIsNone(check.get("execution_allowed"))
        self.assertEqual(item, before)

    def test_late_root_work_is_a_deviation_after_proposed_owner_is_corrected(self):
        result = self.checkpoint(owner="executor", root_started=True, root_start_authorized=False)
        self.assertIs(result.get("deviation"), True)
        self.assertEqual(result.get("next_action"), "delegate_remaining")
        self.assertIs(result.get("preserve_existing_work"), True)

    def test_existing_executor_blocks_root_proposal_and_accepted_work_is_not_redispatched(self):
        assignment = dict(assignment_id="executor-1", role="executor", stage="execution", host_returned=True)
        result = self.checkpoint(assignment=assignment)
        self.assertIs(result.get("execution_allowed"), False)
        self.assertIs(result.get("deviation"), True)
        self.assertEqual(result.get("next_action"), "return_to_executor")
        item = task("work")
        item["execution"] = dict(activity="code", proposed_owner="root", root_started=True, root_start_authorized=False)
        result = readiness([item], ["work"], [], 1, 0, enabled=True)
        check = result["execution_checkpoints"]["work"]
        self.assertEqual(check["next_action"], "no_remaining_work")
        self.assertIs(check["deviation"], True)
        self.assertEqual(result["ready"], [])

    def test_running_without_executor_snapshot_requires_reconciliation_without_duplicate(self):
        item = task("work")
        item["execution"] = dict(activity="code", proposed_owner="root")
        result = readiness([item], [], ["work"], 1, 0, enabled=True)
        check = result.get("execution_checkpoints", {}).get("work", {})
        self.assertEqual(check.get("next_action"), "reconcile_running_assignment")
        self.assertIs(check.get("execution_allowed"), False)
        self.assertEqual(result["ready"], [])

    def test_json_cli_reuses_readiness_and_reports_clean_input_errors(self):
        script = Path(__file__).resolve().parents[1] / "skills/optimax/scripts/work_breakdown.py"
        item = task("work")
        item["execution"] = dict(activity="test_authoring", proposed_owner="root")
        payload = dict(plan=[item], accepted=[], running=[], capacity=1, other_inflight=0, enabled=True)
        completed = subprocess.run([sys.executable, str(script)], input=json.dumps(payload),
                                   capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout or "{}")
        self.assertEqual(result.get("execution_checkpoints", {}).get("work", {}).get("next_action"), "dispatch_executor")
        malformed = subprocess.run([sys.executable, str(script)], input="{", capture_output=True, text=True)
        self.assertEqual(malformed.returncode, 1)
        self.assertIn("error", json.loads(malformed.stderr))
        self.assertNotIn("Traceback", malformed.stderr)

    def test_dispatch_blockers_never_grant_root_fallback_or_override_independent_constraints(self):
        exception = dict(evidence="New user instruction permits root patch", scope="work",
                         authority="new_explicit_user_instruction")
        for blocker in ("budget", "capability", "authentication", "host_policy"):
            with self.subTest(blocker=blocker):
                result = self.checkpoint(dispatch_blocker=blocker, user_exception=exception)
                self.assertEqual(result.get("next_action"), "wait_for_" + blocker)
                self.assertIs(result.get("execution_allowed"), False)

    def test_dispatch_blockers_preserve_existing_executor_and_root_verification(self):
        assignment = dict(assignment_id="native-1", role="executor", stage="execution", host_returned=True)
        for blocker in ("budget", "capability", "authentication", "host_policy"):
            with self.subTest(blocker=blocker):
                result = self.checkpoint(owner="executor", assignment=assignment, dispatch_blocker=blocker)
                self.assertEqual(result.get("next_action"), "continue_executor")
                self.assertIs(result.get("execution_allowed"), True)
                result = self.checkpoint(activity="independent_verification", dispatch_blocker=blocker)
                self.assertEqual(result.get("next_action"), "root_permitted")
        with self.assertRaises(ValueError):
            self.checkpoint(dispatch_blocker="missing_provider_receipt")

    def test_user_exception_does_not_duplicate_existing_executor(self):
        assignment = dict(assignment_id="native-1", role="executor", stage="execution", host_returned=True)
        exception = dict(evidence="New user instruction permits root patch", scope="work",
                         authority="new_explicit_user_instruction")
        result = self.checkpoint(assignment=assignment, user_exception=exception)
        self.assertEqual(result.get("next_action"), "return_to_executor")
        self.assertIs(result.get("execution_allowed"), False)


    def test_current_exception_does_not_claim_unknown_start_history_was_authorized(self):
        exception = dict(evidence="New instruction permits finishing the existing patch",
                         scope="work", authority="new_explicit_user_instruction")
        result = self.checkpoint(root_started=True, user_exception=exception)
        self.assertIsNone(result.get("deviation"))
        self.assertIs(result.get("execution_allowed"), True)
        self.assertEqual(result.get("next_action"), "explicit_user_exception")

    def test_current_exception_preserves_known_start_authorization_history(self):
        exception = dict(evidence="Explicit instruction permitting the remaining patch",
                         scope="work", authority="new_explicit_user_instruction")
        for authorized, deviation in ((False, True), (True, False), (None, None)):
            with self.subTest(authorized=authorized):
                result = self.checkpoint(root_started=True, root_start_authorized=authorized,
                                         user_exception=exception)
                self.assertIs(result.get("root_start_authorized"), authorized)
                self.assertIs(result.get("deviation"), deviation)
                self.assertIs(result.get("execution_allowed"), True)
                self.assertEqual(result.get("next_action"), "explicit_user_exception")
                self.assertIs(result.get("preserve_existing_work"), True)

    def test_historical_authorization_neither_grants_current_permission_nor_duplicates_executor(self):
        result = self.checkpoint(root_started=True, root_start_authorized=True)
        self.assertIs(result.get("deviation"), False)
        self.assertIs(result.get("execution_allowed"), False)
        self.assertEqual(result.get("next_action"), "delegate_remaining")
        assignment = dict(assignment_id="native-1", role="executor", stage="execution", host_returned=True)
        exception = dict(evidence="New instruction permits finishing",
                         scope="work", authority="new_explicit_user_instruction")
        result = self.checkpoint(assignment=assignment, root_started=True,
                                 root_start_authorized=False, user_exception=exception)
        self.assertIs(result.get("deviation"), True)
        self.assertIs(result.get("execution_allowed"), False)
        self.assertEqual(result.get("next_action"), "return_to_executor")
        result = self.checkpoint(owner="executor", assignment=assignment, root_started=True,
                                 root_start_authorized=False, user_exception=exception)
        self.assertIs(result.get("deviation"), True)
        self.assertIs(result.get("execution_allowed"), True)
        self.assertEqual(result.get("next_action"), "continue_executor")

    def test_start_history_is_not_inferred_from_current_mode_owner_or_exception_text(self):
        for owner in ("root", "executor"):
            with self.subTest(owner=owner):
                result = self.checkpoint(owner=owner, root_started=True)
                self.assertIsNone(result.get("deviation"))
                self.assertIsNone(result.get("root_start_authorized"))
        for authorized, deviation in ((False, True), (True, False), (None, None)):
            with self.subTest(off_history=authorized):
                item = task("work")
                item["execution"] = dict(activity="code", proposed_owner="root", root_started=True,
                                         root_start_authorized=authorized)
                result = readiness([item], [], [], 1, 0, enabled=False)["execution_checkpoints"]["work"]
                self.assertIs(result.get("deviation"), deviation)
                self.assertIsNone(result.get("execution_allowed"))
                self.assertEqual(result.get("next_action"), "defer_to_host_policy")

    def test_start_authorization_accepts_only_boolean_or_null_and_does_not_authorize_pending_work(self):
        for invalid in (0, 1, "true", [], {}):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "root_start_authorized"):
                    self.checkpoint(root_started=True, root_start_authorized=invalid)
        for authorized in (False, True, None):
            with self.subTest(pending=authorized):
                result = self.checkpoint(root_start_authorized=authorized)
                self.assertIs(result.get("deviation"), False)
                self.assertIs(result.get("execution_allowed"), False)
                self.assertIsNone(result.get("root_start_authorized"))
                self.assertEqual(result.get("next_action"), "dispatch_executor")

    def test_checkpoint_requires_explicit_actual_mode(self):
        item = task("work")
        item["execution"] = dict(activity="code", proposed_owner="root")
        with self.assertRaisesRegex(ValueError, "enabled"):
            readiness([item], [], [], 1, 0)

    def test_malformed_execution_metadata_is_rejected(self):
        for extra in (None, {}, dict(activity="integration", proposed_owner="root"),
                      dict(activity="code", proposed_owner="root", root_started="yes"),
                      dict(activity="code", proposed_owner="root", assignment={})):
            with self.subTest(execution=extra):
                item = task("work")
                item["execution"] = extra
                with self.assertRaises(ValueError):
                    readiness([item], [], [], 1, 0, enabled=True)


if __name__ == "__main__":
    unittest.main()
