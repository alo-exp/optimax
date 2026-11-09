"""Validate a task plan and determine a feasible, plan-ordered launch set."""

import json
import posixpath
import sys
from graphlib import CycleError, TopologicalSorter

try:
    from .session_policy import ROOT_ACTIVITIES, SUBSTANTIVE_ACTIVITIES, execution_contract
except ImportError:
    from session_policy import ROOT_ACTIVITIES, SUBSTANTIVE_ACTIVITIES, execution_contract


def _execution_metadata(ident, value):
    """Validate a declared host snapshot; this does not authenticate its claims."""
    fields = {"activity", "proposed_owner", "assignment", "root_started", "root_start_authorized",
              "user_exception", "dispatch_blocker"}
    if not isinstance(value, dict) or set(value) - fields:
        raise ValueError("execution must be an object with known fields")
    if value.get("activity") not in (*ROOT_ACTIVITIES, *SUBSTANTIVE_ACTIVITIES):
        raise ValueError("execution activity must describe the actual work")
    if value.get("proposed_owner") not in ("root", "executor", "advisor"):
        raise ValueError("execution proposed_owner must be root, executor, or advisor")
    if type(value.get("root_started", False)) is not bool:
        raise ValueError("execution root_started must be a boolean")
    start_authorized = value.get("root_start_authorized")
    if start_authorized is not None and type(start_authorized) is not bool:
        raise ValueError("execution root_start_authorized must be a boolean or null")
    if "dispatch_blocker" in value and value["dispatch_blocker"] not in ("budget", "capability", "authentication", "host_policy"):
        raise ValueError("dispatch_blocker must be budget, capability, authentication, or host_policy")
    assignment = value.get("assignment")
    if "assignment" in value:
        required = {"assignment_id", "role", "stage", "host_returned"}
        if not isinstance(assignment, dict) or set(assignment) != required:
            raise ValueError("assignment requires assignment_id, role, stage, and host_returned")
        if not isinstance(assignment["assignment_id"], str) or not assignment["assignment_id"].strip():
            raise ValueError("assignment_id must be a nonempty host-returned identifier")
        if assignment["role"] not in ("executor", "advisor") or assignment["stage"] not in ("planning", "design", "execution"):
            raise ValueError("assignment role or stage is invalid")
        if type(assignment["host_returned"]) is not bool:
            raise ValueError("assignment host_returned must be a boolean")
    exception = value.get("user_exception")
    if "user_exception" in value:
        required = {"evidence", "scope", "authority"}
        if not isinstance(exception, dict) or set(exception) != required:
            raise ValueError("user_exception requires concrete evidence, exact scope, and authority")
        if not isinstance(exception["evidence"], str) or not exception["evidence"].strip():
            raise ValueError("user_exception requires concrete instruction evidence")
        if exception["scope"] != ident:
            raise ValueError("user_exception scope must match the exact task ID")
        if exception["authority"] not in ("new_explicit_user_instruction", "higher_priority_governing_instruction"):
            raise ValueError("user_exception requires new explicit user or higher-priority governing authority")
    return value


def _execution_checkpoint(value, enabled, status):
    """Apply current permission separately from declared authorization when root work began."""
    owner = value["proposed_owner"]
    substantive = value["activity"] in SUBSTANTIVE_ACTIVITIES
    assignment = value.get("assignment") or {}
    executor = (assignment.get("host_returned") is True and assignment.get("role") == "executor"
                and assignment.get("stage") == "execution")
    exception = bool(value.get("user_exception"))
    root_started = value.get("root_started", False)
    start_authorized = value.get("root_start_authorized") if root_started else None
    deviation = False
    if substantive and root_started:
        deviation = None if start_authorized is None else not start_authorized
    if enabled and substantive and owner == "root" and executor and not exception:
        deviation = True
    result = dict(execution_allowed=False, next_action="dispatch_executor",
                  ownership_basis="declared_host_snapshot" if executor else None,
                  provider_verified=False, learning_eligible=False, deviation=deviation,
                  root_start_authorized=start_authorized,
                  preserve_existing_work=bool(root_started or executor or status == "accepted"))
    if not enabled:
        result.update(execution_allowed=None, next_action="defer_to_host_policy")
    elif status == "accepted":
        result["next_action"] = "no_remaining_work"
    elif owner == "root" and not substantive:
        result.update(execution_allowed=True, next_action="root_permitted")
    elif status not in ("ready", "running"):
        result["next_action"] = "wait_for_" + status
    elif executor:
        result.update(execution_allowed=owner == "executor",
                      next_action="continue_executor" if owner == "executor" else "return_to_executor")
    elif status == "running":
        result["next_action"] = "reconcile_running_assignment"
    elif value.get("dispatch_blocker"):
        result["next_action"] = "wait_for_" + value["dispatch_blocker"]
    elif owner == "root" and exception:
        result.update(execution_allowed=True, next_action="explicit_user_exception")
    elif root_started:
        result["next_action"] = "delegate_remaining"
    return result


def readiness(plan, accepted, running, capacity, other_inflight=None, *, enabled=None):
    """Return ready IDs, per-ID status, and capacity used after proposed launches.

    Plan is a list of records with nonempty id, outcome and acceptance strings,
    complexity (low/medium/high), and lists of dependencies, write_paths and
    exclusive resources. Lists may be empty. Paths are lexical POSIX paths.
    accepted and running are collections of IDs; only accepted dependencies
    unlock work. other_inflight must be a verified count of occupied slots outside
    running tasks; omitted or unknown occupancy is invalid.
    Plan order is priority; the greedy set is maximal, not maximum cardinality.
    Status values are ready, accepted, running, dependencies, ownership,
    resources, or capacity. Invalid or inconsistent inputs raise ValueError.
    Inputs are never mutated. Optional task.execution metadata adds per-task
    execution_checkpoints using an explicit enabled boolean from current status.
    Assignment and exception evidence are declared host snapshots, not authenticated
    provider receipts. Checkpoints neither dispatch work nor create learning data.
    """
    def strings(value, name):
        if not isinstance(value, (list, tuple, set, frozenset)):
            raise ValueError(f"{name} must be a collection of strings")
        if any(not isinstance(x, str) or not x.strip() for x in value):
            raise ValueError(f"{name} must contain nonempty strings")
        if len(set(value)) != len(value):
            raise ValueError(f"{name} contains duplicates")
        return set(value)

    if not isinstance(plan, list):
        raise ValueError("plan must be a list")
    for name, value in (("capacity", capacity), ("other_inflight", other_inflight)):
        if type(value) is not int or value < 0:
            raise ValueError(f"{name} must be a nonnegative integer")
    entries, execution = {}, {}
    for item in plan:
        if not isinstance(item, dict):
            raise ValueError("task must be a record")
        for field in ("id", "outcome", "acceptance"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"{field} must be a nonempty string")
        ident = item["id"]
        if ident in entries:
            raise ValueError("duplicate task ID")
        if item.get("complexity") not in ("low", "medium", "high"):
            raise ValueError("invalid complexity")
        deps = strings(item.get("dependencies"), "dependencies")
        paths = strings(item.get("write_paths"), "write_paths")
        resources = strings(item.get("resources"), "resources")
        entries[ident] = (deps, {posixpath.normpath(p) for p in paths}, resources)
        if "execution" in item:
            execution[ident] = _execution_metadata(ident, item["execution"])

    if execution or enabled is not None:
        execution_contract(enabled)
    ids = set(entries)
    accepted = strings(accepted, "accepted")
    running = strings(running, "running")
    if not (accepted | running) <= ids or accepted & running:
        raise ValueError("accepted and running IDs must be known and disjoint")
    if len(running) + other_inflight > capacity:
        raise ValueError("occupied slots exceed capacity")
    if any(not deps <= ids for deps, _, _ in entries.values()):
        raise ValueError("unknown dependency")

    try:
        TopologicalSorter({ident: deps for ident, (deps, _, _) in entries.items()}).prepare()
    except CycleError as exc:
        raise ValueError("dependency cycle") from exc
    if any(not entries[ident][0] <= accepted for ident in accepted | running):
        raise ValueError("accepted and running tasks require accepted dependencies")

    def overlap(a, b):
        return a == b or a == "." or b == "." or a.startswith(b.rstrip("/") + "/") or b.startswith(a.rstrip("/") + "/")

    occupied_paths = set()
    occupied_resources = set()
    for ident in running:
        _, paths, resources = entries[ident]
        if any(overlap(a, b) for a in paths for b in occupied_paths) or resources & occupied_resources:
            raise ValueError("running tasks conflict")
        occupied_paths.update(paths)
        occupied_resources.update(resources)

    used = len(running) + other_inflight
    ready, status = [], {}
    for ident, (deps, paths, resources) in entries.items():
        if ident in accepted:
            status[ident] = "accepted"
        elif ident in running:
            status[ident] = "running"
        elif not deps <= accepted:
            status[ident] = "dependencies"
        elif any(overlap(a, b) for a in paths for b in occupied_paths):
            status[ident] = "ownership"
        elif resources & occupied_resources:
            status[ident] = "resources"
        elif used >= capacity:
            status[ident] = "capacity"
        else:
            ready.append(ident)
            status[ident] = "ready"
            used += 1
            occupied_paths.update(paths)
            occupied_resources.update(resources)
    result = {"ready": ready, "status": status, "used_capacity": used}
    if execution:
        result["execution_checkpoints"] = {
            ident: _execution_checkpoint(value, enabled, status[ident])
            for ident, value in execution.items()
        }
    return result


def main():
    """Read one JSON readiness request from stdin; emit JSON without durable writes."""
    try:
        request = json.load(sys.stdin)
        fields = {"plan", "accepted", "running", "capacity", "other_inflight", "enabled"}
        if not isinstance(request, dict) or set(request) - fields:
            raise ValueError("request must be a readiness object with known fields")
        if not {"plan", "accepted", "running", "capacity"} <= set(request):
            raise ValueError("request requires plan, accepted, running, and capacity")
        print(json.dumps(readiness(**request), sort_keys=True))
        return 0
    except (ValueError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
