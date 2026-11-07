"""Validate a task plan and determine a feasible, plan-ordered launch set."""

import posixpath
from graphlib import CycleError, TopologicalSorter


def readiness(plan, accepted, running, capacity, other_inflight=None):
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
    Inputs are never mutated.
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
    entries = {}
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
    return {"ready": ready, "status": status, "used_capacity": used}
