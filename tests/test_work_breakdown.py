import copy
from itertools import product
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

    def test_unsafe_write_paths_are_rejected_before_selection_or_running(self):
        for path in ("..", "../outside", "src/../../outside", "src/\x00file", "//server/share", "///src"):
            for running in ([], ["a"]):
                with self.subTest(path=path, running=running):
                    with self.assertRaisesRegex(ValueError, "write_paths"):
                        readiness([task("a", paths=[path]), task("b", paths=["src/file"])],
                                  [], running, 2, 0)

    def test_write_paths_require_one_namespace_across_the_entire_snapshot(self):
        for paths in ((["/project/src"], ["src/file"]), ([".", "/project/src"], [])):
            for state in ("pending", "running", "accepted"):
                for enabled in (True, False):
                    with self.subTest(paths=paths, state=state, enabled=enabled):
                        with self.assertRaisesRegex(ValueError, "write_paths.*namespace"):
                            readiness([task("a", paths=paths[0]), task("b", paths=paths[1])],
                                      ["a"] if state == "accepted" else [],
                                      ["a"] if state == "running" else [], 2, 0, enabled=enabled)

    def test_normalized_relative_and_absolute_paths_serialize_ancestors(self):
        for parent, child in ((".", "src/file"), ("src/../lib", "lib/file"),
                              ("/", "/src/file"), ("/project/src/../lib", "/project/lib/file")):
            plan = [task("a", paths=[parent]), task("b", paths=[child])]
            for running in ([], ["a"]):
                with self.subTest(parent=parent, child=child, running=running):
                    result = readiness(plan, [], running, 2, 0)
                    self.assertEqual(result["ready"], ["a"] if not running else [])
                    self.assertEqual(result["status"]["b"], "ownership")
            # Accepted history has no current path reservation.
            self.assertEqual(readiness(plan, ["a"], [], 2, 0)["ready"], ["b"])

    def test_normalized_sibling_paths_preserve_component_boundaries(self):
        for first, second in (("src/../lib/a", "lib/ab"),
                              ("/project/lib/a", "/project/lib/ab")):
            plan = [task("a", paths=[first]), task("b", paths=[second])]
            self.assertEqual(readiness(plan, [], [], 2, 0)["ready"], ["a", "b"])
            self.assertEqual(readiness(plan, [], ["a"], 2, 0)["ready"], ["b"])

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
        actual_executor = (assignment is not None and assignment.get("host_returned") is True
                           and assignment.get("role") == "executor" and assignment.get("stage") == "execution")
        result = readiness([item], [], ["work"] if actual_executor else [], 1, 0, enabled=True)
        return result.get("execution_checkpoints", {}).get("work", {})

    def test_actual_executor_assignment_requires_running_or_accepted_task(self):
        assignment = dict(assignment_id="executor-1", role="executor", stage="execution", host_returned=True)
        for enabled in (True, False):
            for other in (0, 1):
                for owner in ("root", "executor"):
                    for activity in ("code", "independent_verification"):
                        with self.subTest(enabled=enabled, other=other, owner=owner, activity=activity):
                            item = task("work")
                            item["execution"] = dict(activity=activity, proposed_owner=owner,
                                                     assignment=assignment, dispatch_blocker="budget")
                            with self.assertRaisesRegex(ValueError, "assignment.*running or accepted"):
                                readiness([item], [], [], 2, other, enabled=enabled)

    def test_actual_executor_running_occupancy_and_historical_acceptance(self):
        assignment = dict(assignment_id="executor-1", role="executor", stage="execution", host_returned=True)
        item = task("work", paths=["src"], resources=["db"])
        item["execution"] = dict(activity="code", proposed_owner="executor", assignment=assignment)
        for enabled in (True, False):
            with self.subTest(enabled=enabled):
                running = readiness([item, task("free")], [], ["work"], 3, 1, enabled=enabled)
                self.assertEqual(running["ready"], ["free"])
                self.assertEqual(running["used_capacity"], 3)
                self.assertEqual(running["status"]["work"], "running")
                historical = readiness([item, task("next", ["work"], ["src"], ["db"])],
                                       ["work"], [], 2, 1, enabled=enabled)
                self.assertEqual(historical["ready"], ["next"])
                self.assertEqual(historical["used_capacity"], 2)
                self.assertEqual(historical["status"]["work"], "accepted")

    def test_historical_executor_does_not_invent_current_ownership_deviation(self):
        assignment = dict(assignment_id="executor-1", role="executor", stage="execution", host_returned=True)
        for status in ("accepted", "running"):
            for enabled in (True, False):
                for exception in (False, True):
                    for started, authorized in ((False, None), (True, True), (True, False), (True, None)):
                        with self.subTest(status=status, enabled=enabled, exception=exception,
                                          started=started, authorized=authorized):
                            item = task("work")
                            item["execution"] = dict(activity="code", proposed_owner="root",
                                                     assignment=assignment, root_started=started,
                                                     root_start_authorized=authorized)
                            if exception:
                                item["execution"]["user_exception"] = dict(evidence="New explicit permission",
                                    scope="work", authority="new_explicit_user_instruction")
                            result = readiness([item], ["work"] if status == "accepted" else [],
                                               ["work"] if status == "running" else [], 1, 0, enabled=enabled)
                            check = result["execution_checkpoints"]["work"]
                            expected = (None if authorized is None else not authorized) if started else False
                            if status == "running" and enabled and not exception:
                                expected = True
                            self.assertIs(check["deviation"], expected)
                            self.assertIs(check["root_start_authorized"], authorized if started else None)
                            self.assertEqual(result["ready"], [])
                            if not enabled:
                                action = "defer_to_host_policy"
                            else:
                                action = "no_remaining_work" if status == "accepted" else "return_to_executor"
                            self.assertEqual(check["next_action"], action)

    def test_duplicate_current_executor_assignment_ids_are_rejected(self):
        assignment = dict(assignment_id="executor-1", role="executor", stage="execution", host_returned=True)
        plan = [task("one"), task("two")]
        for item in plan:
            item["execution"] = dict(activity="code", proposed_owner="executor", assignment=assignment)
        for enabled in (True, False):
            with self.subTest(enabled=enabled):
                with self.assertRaisesRegex(ValueError, "duplicate.*assignment"):
                    readiness(plan, [], ["one", "two"], 2, 0, enabled=enabled)
                # Accepted assignments are historical and do not claim a second live slot.
                result = readiness(plan, ["one"], ["two"], 1, 0, enabled=enabled)
                self.assertEqual(result["ready"], [])
                self.assertEqual(result["used_capacity"], 1)

    def test_nonqualifying_assignments_and_legacy_snapshots_remain_schedulable(self):
        assignment = dict(assignment_id="executor-1", role="executor", stage="execution", host_returned=True)
        for change in (dict(role="advisor"), dict(stage="planning"), dict(stage="design"),
                       dict(host_returned=False)):
            for enabled in (True, False):
                with self.subTest(change=change, enabled=enabled):
                    item = task("work")
                    item["execution"] = dict(activity="code", proposed_owner="executor",
                                             assignment=dict(assignment, **change))
                    result = readiness([item], [], [], 1, 0, enabled=enabled)
                    self.assertEqual(result["ready"], ["work"])
                    self.assertEqual(result["used_capacity"], 1)
        self.assertEqual(readiness([task("legacy")], [], [], 1, 0)["ready"], ["legacy"])

    def test_dispatch_blockers_do_not_reserve_capacity_paths_or_resources(self):
        for blocker in ("budget", "capability", "authentication", "host_policy"):
            for conflict in ("capacity", "path", "resource"):
                with self.subTest(blocker=blocker, conflict=conflict):
                    paths = ["src"] if conflict == "path" else []
                    resources = ["db"] if conflict == "resource" else []
                    blocked = task("blocked", paths=paths, resources=resources)
                    blocked["execution"] = dict(activity="code", proposed_owner="executor",
                                                dispatch_blocker=blocker)
                    other = task("other", paths=paths, resources=resources)
                    result = readiness([blocked, other], [], [], 1 if conflict == "capacity" else 2,
                                       0, enabled=True)
                    self.assertEqual(result["ready"], ["other"])
                    self.assertEqual(result["status"]["blocked"], blocker)
                    self.assertEqual(result["used_capacity"], 1)
                    self.assertEqual(result["execution_checkpoints"]["blocked"]["next_action"],
                                     "wait_for_" + blocker)

    def test_blocker_preflight_preserves_checkpoint_precedence(self):
        item = task("work")
        item["execution"] = dict(activity="code", proposed_owner="root", dispatch_blocker="budget")
        self.assertEqual(readiness([item], ["work"], [], 1, 0, enabled=True)["status"]["work"], "accepted")
        self.assertEqual(readiness([item], [], ["work"], 1, 0, enabled=True)["status"]["work"], "running")
        dependent = dict(item, dependencies=["dep"])
        self.assertEqual(readiness([task("dep"), dependent], [], [], 2, 0, enabled=True)["status"]["work"], "dependencies")
        self.assertEqual(readiness([item], [], [], 1, 0, enabled=False)["ready"], ["work"])
        root = dict(item, execution=dict(activity="independent_verification", proposed_owner="root",
                                         dispatch_blocker="budget"))
        self.assertEqual(readiness([root], [], [], 1, 0, enabled=True)["ready"], ["work"])
        assignment = dict(assignment_id="executor-1", role="executor", stage="execution", host_returned=True)
        assigned = dict(item, execution=dict(item["execution"], assignment=assignment))
        assigned_result = readiness([assigned], [], ["work"], 1, 0, enabled=True)
        self.assertEqual(assigned_result["ready"], [])
        self.assertEqual(assigned_result["execution_checkpoints"]["work"]["next_action"], "return_to_executor")
        exception = dict(evidence="explicit permission", scope="work", authority="new_explicit_user_instruction")
        permitted = dict(item, execution=dict(activity="code", proposed_owner="root", user_exception=exception))
        self.assertEqual(readiness([permitted], [], [], 1, 0, enabled=True)["ready"], ["work"])

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

    def test_root_nonsubstantive_checkpoint_respects_readiness(self):
        activities = ("coordination", "source_inspection", "independent_verification", "acceptance")
        cases = (
            ("dependencies", [task("dep"), task("work", ["dep"])], [], [], 2, 0, True, False, "wait_for_dependencies"),
            ("ownership", [task("other", paths=["src"]), task("work", paths=["src/file"])], [], [], 2, 0, True, False, "wait_for_ownership"),
            ("resources", [task("other", resources=["db"]), task("work", resources=["db"])], [], [], 2, 0, True, False, "wait_for_resources"),
            ("ready", [task("work")], [], [], 0, 0, True, True, "root_permitted"),
            ("ready", [task("work")], [], [], 1, 0, True, True, "root_permitted"),
            ("running", [task("work")], [], ["work"], 1, 0, True, True, "root_permitted"),
            ("accepted", [task("work")], ["work"], [], 1, 0, True, False, "no_remaining_work"),
            ("ready", [task("work")], [], [], 0, 0, False, None, "defer_to_host_policy"),
        )
        for activity in activities:
            for status, plan, accepted, running, capacity, other, enabled, allowed, action in cases:
                with self.subTest(activity=activity, status=status, enabled=enabled):
                    plan[-1]["execution"] = dict(activity=activity, proposed_owner="root")
                    result = readiness(plan, accepted, running, capacity, other, enabled=enabled)
                    self.assertEqual(result["status"]["work"], status)
                    checkpoint = result["execution_checkpoints"]["work"]
                    self.assertIs(checkpoint["execution_allowed"], allowed)
                    self.assertEqual(checkpoint["next_action"], action)

    def test_explicit_root_verification_uses_no_helper_slot(self):
        for enabled in (True, False):
            for running in ([], ["verify"]):
                for capacity, other in ((0, 0), (1, 1)):
                    with self.subTest(enabled=enabled, running=running, capacity=capacity, other=other):
                        root = task("verify")
                        root["execution"] = dict(activity="independent_verification", proposed_owner="root")
                        result = readiness([root], [], running, capacity, other, enabled=enabled)
                        self.assertEqual(result["ready"], [] if running else ["verify"])
                        self.assertEqual(result["used_capacity"], other)
                        check = result["execution_checkpoints"]["verify"]
                        self.assertEqual(check["next_action"], "root_permitted" if enabled else "defer_to_host_policy")
                        self.assertIs(check["execution_allowed"], True if enabled else None)

    def test_actual_executor_precedes_root_activity_permission(self):
        assignment = dict(assignment_id="executor-1", role="executor", stage="execution", host_returned=True)
        for activity in ("coordination", "source_inspection", "independent_verification", "acceptance"):
            for state in ("running", "accepted"):
                for enabled in (True, False):
                    for exception in (True, False):
                        with self.subTest(activity=activity, state=state, enabled=enabled, exception=exception):
                            item = task("work")
                            item["execution"] = dict(activity=activity, proposed_owner="root", assignment=assignment)
                            if exception:
                                item["execution"]["user_exception"] = dict(evidence="New explicit permission",
                                    scope="work", authority="new_explicit_user_instruction")
                            result = readiness([item], ["work"] if state == "accepted" else [],
                                               ["work"] if state == "running" else [], 1, 0, enabled=enabled)
                            check = result["execution_checkpoints"]["work"]
                            if not enabled:
                                action = "defer_to_host_policy"
                            else:
                                action = "no_remaining_work" if state == "accepted" else "return_to_executor"
                            self.assertEqual(check["next_action"], action)
                            self.assertIs(check["execution_allowed"], False if enabled else None)
                            self.assertIs(check["preserve_existing_work"], True)
                            self.assertEqual(result["ready"], [])
                            self.assertEqual(result["used_capacity"], 1 if state == "running" else 0)

    def test_root_helper_assignment_lifecycle_and_slot_matrix(self):
        cases = product(("advisor", "executor"), ("planning", "design", "execution"),
                        (True, False), ("pending", "running", "accepted"), (True, False), (0, 1))
        for role, stage, returned, state, enabled, other in cases:
            with self.subTest(role=role, stage=stage, returned=returned, state=state, enabled=enabled, other=other):
                item = task("root")
                item["execution"] = dict(activity="coordination", proposed_owner="root",
                    assignment=dict(assignment_id="helper-1", role=role, stage=stage, host_returned=returned))
                accepted = ["root"] if state == "accepted" else []
                running = ["root"] if state == "running" else []
                if state == "pending" and returned:
                    with self.assertRaisesRegex(ValueError, "assignment.*running or accepted"):
                        readiness([item], accepted, running, 1 + other, other, enabled=enabled)
                    continue
                result = readiness([item], accepted, running, 1 + other, other, enabled=enabled)
                self.assertEqual(result["used_capacity"], other + int(state == "running" and returned))
                self.assertEqual(result["ready"], ["root"] if state == "pending" else [])
                check = result["execution_checkpoints"]["root"]
                self.assertIs(check["preserve_existing_work"], state == "accepted" or (state == "running" and returned))
                action = "root_permitted"
                if state == "accepted":
                    action = "no_remaining_work"
                elif returned and role == "executor" and stage == "execution":
                    action = "return_to_executor"
                self.assertEqual(check["next_action"], action if enabled else "defer_to_host_policy")
                if state == "running" and returned:
                    with self.assertRaisesRegex(ValueError, "occupied slots"):
                        readiness([item], accepted, running, other, other, enabled=enabled)
                filled = readiness([item, task("free")], accepted, running, 1 + other, other, enabled=enabled)
                expected = [] if state == "running" and returned else ["free"]
                if state == "pending":
                    expected.insert(0, "root")
                self.assertEqual(filled["ready"], expected)

    def test_running_root_tasks_cannot_duplicate_one_returned_helper(self):
        for enabled in (True, False):
            plan = [task("one"), task("two")]
            for item in plan:
                item["execution"] = dict(activity="coordination", proposed_owner="root",
                    assignment=dict(assignment_id="advisor-1", role="advisor", stage="planning", host_returned=True))
            with self.subTest(enabled=enabled):
                with self.assertRaisesRegex(ValueError, "duplicate.*assignment"):
                    readiness(plan, [], ["one", "two"], 2, 0, enabled=enabled)
                historical = readiness(plan, ["one"], ["two"], 1, 0, enabled=enabled)
                self.assertEqual(historical["used_capacity"], 1)

    def test_all_running_returned_helper_ids_are_unique(self):
        cases = product(("advisor", "executor"), ("planning", "design", "execution"),
                        (("code", "code"), ("coordination", "code"), ("code", "coordination")), (True, False))
        for role, stage, activities, enabled in cases:
            with self.subTest(role=role, stage=stage, activities=activities, enabled=enabled):
                plan = [task("one"), task("two")]
                for item, activity in zip(plan, activities):
                    item["execution"] = dict(activity=activity, proposed_owner="root",
                        assignment=dict(assignment_id="helper-1", role=role, stage=stage, host_returned=True))
                with self.assertRaisesRegex(ValueError, "duplicate.*assignment"):
                    readiness(plan, [], ["one", "two"], 2, 0, enabled=enabled)
                # Accepted evidence is historical, including the same returned ID.
                historical = readiness(plan, ["one"], ["two"], 1, 0, enabled=enabled)
                self.assertEqual(historical["used_capacity"], 1)
                # Distinct actual helpers are distinct occupied slots.
                plan[1]["execution"]["assignment"]["assignment_id"] = "helper-2"
                distinct = readiness(plan, [], ["one", "two"], 2, 0, enabled=enabled)
                self.assertEqual(distinct["used_capacity"], 2)

    def test_pending_substantive_advisor_context_is_not_a_running_identity_claim(self):
        for enabled in (True, False):
            plan = [task("running"), task("pending"), task("accepted")]
            for item in plan:
                item["execution"] = dict(activity="code", proposed_owner="executor",
                    assignment=dict(assignment_id="advisor-1", role="advisor", stage="planning", host_returned=True))
            result = readiness(plan, ["accepted"], ["running"], 2, 0, enabled=enabled)
            self.assertEqual(result["ready"], ["pending"])
            self.assertEqual(result["used_capacity"], 2)

    def test_non_boolean_host_receipts_cannot_establish_root_helper_occupancy(self):
        for returned in (None, 0, 1, "true"):
            item = task("root")
            item["execution"] = dict(activity="coordination", proposed_owner="root",
                assignment=dict(assignment_id="helper-1", role="advisor", stage="planning", host_returned=returned))
            with self.subTest(returned=returned):
                with self.assertRaisesRegex(ValueError, "host_returned must be a boolean"):
                    readiness([item], [], ["root"], 1, 0, enabled=True)

    def test_root_work_does_not_suppress_independent_executor_selection(self):
        for activity in ("coordination", "source_inspection", "independent_verification", "acceptance"):
            for enabled in (True, False):
                for running in ([], ["root"]):
                    with self.subTest(activity=activity, enabled=enabled, running=running):
                        root = task("root", paths=["root-output"], resources=["root-resource"])
                        root["execution"] = dict(activity=activity, proposed_owner="root")
                        result = readiness([root, task("executor")], [], running, 1, 0, enabled=enabled)
                        self.assertEqual(result["ready"], ["executor"] if running else ["root", "executor"])
                        self.assertEqual(result["used_capacity"], 1)

    def test_root_slot_exemption_requires_explicit_root_activity_without_live_executor(self):
        assignment = dict(assignment_id="executor-1", role="executor", stage="execution", host_returned=True)
        for metadata in (None, dict(activity="code", proposed_owner="root"),
                         dict(activity="independent_verification", proposed_owner="executor"),
                         dict(activity="independent_verification", proposed_owner="root", assignment=assignment)):
            with self.subTest(metadata=metadata):
                item = task("work")
                if metadata is not None:
                    item["execution"] = metadata
                running = ["work"] if metadata and "assignment" in metadata else []
                if running:
                    with self.assertRaisesRegex(ValueError, "occupied slots"):
                        readiness([item], [], running, 0, 0, enabled=True)
                else:
                    result = readiness([item], [], [], 0, 0, enabled=True)
                    self.assertEqual(result["status"]["work"], "capacity")
                    self.assertEqual(result["ready"], [])

    def test_root_slot_exemption_preserves_selected_and_running_resource_conflicts(self):
        for conflict in ("ownership", "resources"):
            for running in ([], ["root"]):
                for enabled in (True, False):
                    with self.subTest(conflict=conflict, running=running, enabled=enabled):
                        paths = ["src"] if conflict == "ownership" else []
                        resources = ["db"] if conflict == "resources" else []
                        root = task("root", paths=paths, resources=resources)
                        root["execution"] = dict(activity="independent_verification", proposed_owner="root")
                        other = task("executor", paths=paths, resources=resources)
                        result = readiness([root, other], [], running, 1, 0, enabled=enabled)
                        self.assertEqual(result["ready"], [] if running else ["root"])
                        self.assertEqual(result["status"]["executor"], conflict)
                        self.assertEqual(result["used_capacity"], 0)

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

    def test_root_exception_continuation_requires_known_root_work_without_returned_helper(self):
        advisor = dict(assignment_id="helper-1", role="advisor", stage="planning", host_returned=True)
        executor = dict(advisor, role="executor", stage="execution")
        cases = product(("running", "accepted"), (True, False), (True, False), (True, False),
                        (None, dict(advisor, host_returned=False), advisor, executor),
                        (None, "budget", "capability", "authentication", "host_policy"), (True, False, None))
        for state, enabled, exception, started, assignment, blocker, authorized in cases:
            with self.subTest(state=state, enabled=enabled, exception=exception, started=started,
                              assignment=assignment, blocker=blocker, authorized=authorized):
                item = task("work")
                metadata = dict(activity="code", proposed_owner="root", root_started=started,
                                root_start_authorized=authorized)
                if assignment is not None:
                    metadata["assignment"] = assignment
                if blocker is not None:
                    metadata["dispatch_blocker"] = blocker
                if exception:
                    metadata["user_exception"] = dict(evidence="New explicit permission", scope="work",
                                                      authority="new_explicit_user_instruction")
                item["execution"] = metadata
                result = readiness([item], ["work"] if state == "accepted" else [],
                                   ["work"] if state == "running" else [], 1, 0, enabled=enabled)
                check = result["execution_checkpoints"]["work"]
                returned = assignment is not None and assignment["host_returned"]
                allowed = state == "running" and exception and started and not returned
                action = "explicit_user_exception" if allowed else "reconcile_running_assignment"
                if assignment == executor:
                    allowed, action = False, "return_to_executor"
                if state == "accepted":
                    allowed, action = False, "no_remaining_work"
                if not enabled:
                    allowed, action = None, "defer_to_host_policy"
                self.assertEqual(check["next_action"], action)
                self.assertIs(check["execution_allowed"], allowed)
                history = (None if authorized is None else not authorized) if started else False
                if enabled and state == "running" and assignment == executor and not exception:
                    history = True
                self.assertIs(check["deviation"], history)
                self.assertEqual(result["ready"], [])
                self.assertEqual(result["used_capacity"], int(state == "running"))

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
