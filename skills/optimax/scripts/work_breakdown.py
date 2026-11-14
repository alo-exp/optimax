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


def _returned_helper(value):
    return (value.get("assignment") or {}).get("host_returned") is True


def _root_activity(value):
    return value.get("proposed_owner") == "root" and value.get("activity") in ROOT_ACTIVITIES


def _actual_executor(value):
    assignment = value.get("assignment") or {}
    return (_returned_helper(value) and assignment.get("role") == "executor"
            and assignment.get("stage") == "execution")


def _validate_assignment_lifecycle(execution, accepted, running):
    current_assignments = set()
    for ident, value in execution.items():
        if not _returned_helper(value):
            continue
        if ident not in running | accepted and (_actual_executor(value) or _root_activity(value)):
            raise ValueError("host-returned helper assignment requires task to be running or accepted")
        if ident in running:
            assignment_id = value["assignment"]["assignment_id"]
            if assignment_id in current_assignments:
                raise ValueError("duplicate current helper assignment ID")
            current_assignments.add(assignment_id)


def _execution_checkpoint(value, enabled, status):
    """Apply current permission separately from declared authorization when root work began."""
    owner = value["proposed_owner"]
    substantive = value["activity"] in SUBSTANTIVE_ACTIVITIES
    executor = _actual_executor(value)
    exception = bool(value.get("user_exception"))
    root_started = value.get("root_started", False)
    start_authorized = value.get("root_start_authorized") if root_started else None
    deviation = False
    if substantive and root_started:
        deviation = None if start_authorized is None else not start_authorized
    if enabled and status == "running" and substantive and owner == "root" and executor and not exception:
        deviation = True
    result = dict(execution_allowed=False, next_action="dispatch_executor",
                  ownership_basis="declared_host_snapshot" if executor else None,
                  provider_verified=False, learning_eligible=False, deviation=deviation,
                  root_start_authorized=start_authorized,
                  preserve_existing_work=bool(root_started or executor or status == "accepted"
                                              or (status == "running" and _returned_helper(value))))
    if not enabled:
        result.update(execution_allowed=None, next_action="defer_to_host_policy")
    elif status == "accepted":
        result["next_action"] = "no_remaining_work"
    elif status not in ("ready", "running"):
        result["next_action"] = "wait_for_" + status
    elif executor:
        result.update(execution_allowed=owner == "executor",
                      next_action="continue_executor" if owner == "executor" else "return_to_executor")
    elif owner == "root" and not substantive:
        result.update(execution_allowed=True, next_action="root_permitted")
    elif status == "running":
        if owner == "root" and exception and root_started and not _returned_helper(value):
            result.update(execution_allowed=True, next_action="explicit_user_exception")
        else:
            result["next_action"] = "reconcile_running_assignment"
    elif value.get("dispatch_blocker"):
        result["next_action"] = "wait_for_" + value["dispatch_blocker"]
    elif owner == "root" and exception:
        result.update(execution_allowed=True, next_action="explicit_user_exception")
    elif root_started:
        result["next_action"] = "delegate_remaining"
    return result


def _normalized_write_paths(paths):
    normalized = set()
    for path in paths:
        if "\x00" in path or path.startswith("//"):
            raise ValueError("write_paths cannot contain NUL or multiple leading slashes")
        path = posixpath.normpath(path)
        if path == ".." or path.startswith("../"):
            raise ValueError("write_paths must stay within the project-relative root")
        normalized.add(path)
    return normalized


def _helper_slot_cost(value):
    return 0 if _root_activity(value) and not _returned_helper(value) else 1


def readiness(plan, accepted, running, capacity, other_inflight=None, *, enabled=None):
    """Return ready IDs, per-ID status, and capacity used after proposed launches.

    Plan is a list of records with nonempty id, outcome and acceptance strings,
    complexity (low/medium/high), and lists of dependencies, write_paths and
    exclusive resources. Lists may be empty. Paths use one lexical POSIX namespace:
    project-relative paths confined to root, or absolute paths. NUL, multiple leading
    slashes, relative escapes and mixed namespaces are invalid.
    accepted and running are collections of IDs; only accepted dependencies
    unlock work. other_inflight must be a verified count of occupied slots outside
    running tasks; omitted or unknown occupancy is invalid. Capacity counts helper
    slots: explicit root activities without a host-returned helper assignment cost zero,
    while tasks without that metadata retain one-slot accounting. Root tasks still
    reserve paths/resources and require accepted dependencies.
    Plan order is priority; the greedy set is maximal, not maximum cardinality.
    Status values include ready, accepted, running, dependencies, ownership,
    resources, capacity, or a declared dispatch blocker. Blocked dispatches do
    not reserve capacity, paths, or resources. Invalid inputs raise ValueError.
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
        entries[ident] = (deps, _normalized_write_paths(paths), resources)
        if "execution" in item:
            execution[ident] = _execution_metadata(ident, item["execution"])

    namespaces = {posixpath.isabs(path) for _, paths, _ in entries.values() for path in paths}
    if len(namespaces) > 1:
        raise ValueError("write_paths must share one relative or absolute POSIX namespace")
    if execution or enabled is not None:
        execution_contract(enabled)
    ids = set(entries)
    accepted = strings(accepted, "accepted")
    running = strings(running, "running")
    if not (accepted | running) <= ids or accepted & running:
        raise ValueError("accepted and running IDs must be known and disjoint")

    _validate_assignment_lifecycle(execution, accepted, running)
    slot_cost = {ident: _helper_slot_cost(execution.get(ident, {})) for ident in entries}
    used = sum(slot_cost[ident] for ident in running) + other_inflight
    if used > capacity:
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

    ready, status = [], {}
    for ident, (deps, paths, resources) in entries.items():
        if ident in accepted:
            status[ident] = "accepted"
        elif ident in running:
            status[ident] = "running"
        elif not deps <= accepted:
            status[ident] = "dependencies"
        elif (enabled and ident in execution and execution[ident].get("dispatch_blocker")
              and _execution_checkpoint(execution[ident], enabled, "ready")["next_action"]
              == "wait_for_" + execution[ident]["dispatch_blocker"]):
            status[ident] = execution[ident]["dispatch_blocker"]
        elif any(overlap(a, b) for a in paths for b in occupied_paths):
            status[ident] = "ownership"
        elif resources & occupied_resources:
            status[ident] = "resources"
        elif used + slot_cost[ident] > capacity:
            status[ident] = "capacity"
        else:
            ready.append(ident)
            status[ident] = "ready"
            used += slot_cost[ident]
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
