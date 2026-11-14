"""Recommend a supported logical model/effort rung without changing files.

API: recommend(request: dict) -> dict. CLI:
    python3 scripts/ladder.py REQUEST.json

Request schema:
    {"track": {"platform": "claude"|"codex", "role": "executor"|"advisor",
               "tier": "low"|"medium"|"high"|"business_doc"|null, "step": int,
               "model_id": nonempty str, "epoch": nonempty str},
     "available_steps": [unique supported integer indices for this ladder],
     "assessments": [{all track fields, "run_id": nonempty str,
                      "timestamp": timezone-aware ISO8601 str,
                      "score": integer 0..5, "verified": bool}]}

Executor tracks require a complexity tier; advisor tracks require tier=null and
have one ladder per platform with no complexity tiers. Business-document tier is
executor-only. Indices are zero-based. Executor steps must meet the tier floor.
For v3/v4 Advisors, supply the actual recorded step even below a newly raised
consultation floor; the lowest supported rung at or above the floor is selected
with context_floor_raised and reset_required. Both track.step and assessment.step describe
the independently established effective model/effort rung, rather than only a
requested rung. The caller supplies verified exact model IDs; this helper does
not verify provider identity or resolve aliases. Logical families below contain
no fixed versions. Optional request.policy_version selects a frozen v1/v2/v3
registry for historical replay; the default is optimal-ultra-ladder-v4. Unknown
policy versions are rejected. Current Advisor requests accept advice_level
medium/high/super_high (default medium), constraining the minimum supported rung
to 0/1/2 without creating separate performance tracks.

Every supplied assessment field is validated, including excluded records.
Missing fields, unverified records, and other exact tracks are excluded.
Duplicate supplied run IDs are rejected globally. Sort by UTC timestamp, with
input order breaking ties. The newest five eligible records determine movement:
average <=4.5 moves up; five perfect scores move down; otherwise stay. Fewer
than five never cause performance movement. Skip unsupported rungs. A currently
unavailable rung requires the next supported higher rung regardless of scores;
raise ValueError if none exists.

Output keys: selected_step, selected_family, selected_effort, reason,
eligible_count (all matching verified records, before newest-five selection),
excluded_count (all other records), window_run_ids (chronological newest up to
five), average (null until five eligible records), reset_required.
Reasons: insufficient_evidence, low_performance, perfect_performance,
performance_stable, floor_reached, ceiling_reached, capability_fallback,
context_floor_raised.
Movement sets reset_required=true. The caller creates and persists the fresh
epoch; this helper never creates an epoch or writes files. Invalid inputs raise
ValueError. CLI failures exit nonzero with one compact stderr error line.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys


LEGACY_POLICY_VERSION = "optimal-ultra-ladder-v1"
SECOND_POLICY_VERSION = "optimal-ultra-ladder-v2"
THIRD_POLICY_VERSION = "optimal-ultra-ladder-v3"
POLICY_VERSION = "optimal-ultra-ladder-v4"
ADVICE_FLOORS = {"medium": 0, "high": 1, "super_high": 2}
_LEGACY_LADDERS = {
    ("claude", "executor"): (
        ("haiku", "xhigh"), ("haiku", "max"), ("sonnet", "high"),
        ("sonnet", "xhigh"), ("opus", "low"), ("opus", "medium"),
    ),
    ("codex", "executor"): (
        ("luna", "max"), ("sol", "high"), ("sol", "xhigh"), ("sol", "max"),
    ),
    ("claude", "advisor"): (("opus", "medium"), ("opus", "high")),
    ("codex", "advisor"): (("sol", "xhigh"), ("sol", "max")),
}
_TRACK_FIELDS = ("platform", "role", "tier", "step", "model_id", "epoch")
_ASSESSMENT_FIELDS = (*_TRACK_FIELDS, "run_id", "timestamp", "score", "verified")
_LEGACY_FLOORS = {
    "claude": {"low": 0, "medium": 1, "high": 2, "business_doc": 3},
    "codex": {"low": 0, "medium": 1, "high": 2, "business_doc": 2},
}


_V2_LADDERS = {
    ("claude", "executor"): (
        ("haiku", "high"), ("haiku", "xhigh"), ("haiku", "max"),
        ("sonnet", "high"), ("opus", "medium"), ("opus", "high"),
    ),
    ("codex", "executor"): (
        ("terra", "low"), ("terra", "medium"), ("terra", "high"),
        ("sol", "medium"), ("sol", "high"), ("sol", "xhigh"), ("sol", "max"),
    ),
    ("claude", "advisor"): _LEGACY_LADDERS[("claude", "advisor")],
    ("codex", "advisor"): _LEGACY_LADDERS[("codex", "advisor")],
}
_FLOORS = {
    "claude": {"low": 0, "medium": 2, "high": 3, "business_doc": 4},
    "codex": {"low": 0, "medium": 1, "high": 2, "business_doc": 5},
}


_V3_LADDERS = dict(_V2_LADDERS)
_V3_LADDERS.update({
    ("claude", "advisor"): (("opus", "medium"), ("opus", "high"), ("opus", "xhigh")),
    ("codex", "advisor"): (("sol", "xhigh"), ("sol", "max"), ("astra", "max")),
})
_LADDERS = dict(_V3_LADDERS)
_LADDERS[("claude", "advisor")] = (*_V3_LADDERS[("claude", "advisor")], ("opus", "max"))


def policy_lineage(version, role, platform=None):
    """Identify definitions whose unchanged epochs may share evidence."""
    policy(version)
    if role not in ("executor", "advisor"):
        raise ValueError("invalid role")
    if platform is not None and platform not in ("claude", "codex"):
        raise ValueError("invalid platform")
    if role == "executor":
        return "executor-v1" if version == LEGACY_POLICY_VERSION else "executor-v2"
    if version == POLICY_VERSION:
        if platform is None:
            raise ValueError("platform required for current Advisor lineage")
        return "advisor-v4" if platform == "claude" else "advisor-v3"
    return "advisor-v3" if version == THIRD_POLICY_VERSION else "advisor-v1"


def policy(version=POLICY_VERSION):
    """Return a known immutable-by-convention version's ladder and floor maps."""
    if version == LEGACY_POLICY_VERSION:
        return _LEGACY_LADDERS, _LEGACY_FLOORS
    if version == SECOND_POLICY_VERSION:
        return _V2_LADDERS, _FLOORS
    if version == THIRD_POLICY_VERSION:
        return _V3_LADDERS, _FLOORS
    if version == POLICY_VERSION:
        return _LADDERS, _FLOORS
    raise ValueError("unsupported policy version")


def _nonempty_string(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be a timezone-aware ISO8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timezone required")
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise ValueError("timestamp must be a timezone-aware ISO8601 string") from None


def _validate_fields(record, ladders):
    """Validate present fields; absent assessment attribution remains excludable."""
    for key in ("platform", "role", "model_id", "epoch", "run_id"):
        if key in record:
            _nonempty_string(record[key], key)
    if "platform" in record and record["platform"] not in ("claude", "codex"):
        raise ValueError("platform must be claude or codex")
    if "role" in record and record["role"] not in ("executor", "advisor"):
        raise ValueError("role must be executor or advisor")
    if "tier" in record:
        if record.get("role") == "advisor":
            if record["tier"] is not None:
                raise ValueError("advisor has no complexity tier; use null")
        elif (record["tier"] not in ("low", "medium", "high", "business_doc")
              and not ("role" not in record and record["tier"] is None)):
            raise ValueError("invalid executor tier")
    if "step" in record:
        step = record["step"]
        if type(step) is not int or step < 0:
            raise ValueError("step must be a nonnegative integer index")
        if "platform" in record and "role" in record:
            if step >= len(ladders[(record["platform"], record["role"])]):
                raise ValueError("step is outside its ladder")
    if "score" in record and (type(record["score"]) is not int or not 0 <= record["score"] <= 5):
        raise ValueError("score must be an integer from 0 to 5")
    if "verified" in record and type(record["verified"]) is not bool:
        raise ValueError("verified must be a boolean")
    return _timestamp(record["timestamp"]) if "timestamp" in record else None


def recommend(request):
    """Return a deterministic, read-only recommendation; invalid inputs raise ValueError."""
    if not isinstance(request, dict):
        raise ValueError("request must be an object")
    ladders, floors = policy(request.get("policy_version", POLICY_VERSION))
    track = request.get("track")
    if not isinstance(track, dict) or any(key not in track for key in _TRACK_FIELDS):
        raise ValueError("track must include platform, role, tier, step, model_id, and epoch")
    _validate_fields(track, ladders)
    ladder = ladders[(track["platform"], track["role"])]
    floor = 0 if track["role"] == "advisor" else floors[track["platform"]][track["tier"]]
    contextual = track["role"] == "advisor" and request.get("policy_version", POLICY_VERSION) in (THIRD_POLICY_VERSION, POLICY_VERSION)
    if contextual:
        level = request.get("advice_level", "medium")
        if not isinstance(level, str) or level not in ADVICE_FLOORS:
            raise ValueError("advice_level must be medium, high, or super_high")
        floor = ADVICE_FLOORS[level]
    current = track["step"]
    if current < floor and not contextual:
        raise ValueError("current step is below the tier starting floor")
    available = request.get("available_steps")
    if not isinstance(available, list) or not available:
        raise ValueError("available_steps must be a nonempty list")
    if any(type(step) is not int or not 0 <= step < len(ladder) for step in available):
        raise ValueError("available_steps must contain integer indices within the ladder")
    if len(set(available)) != len(available):
        raise ValueError("available_steps must be unique")
    supported = sorted(step for step in available if step >= floor)
    if not supported:
        raise ValueError("no supported rung at or above the tier floor")
    records = request.get("assessments")
    if not isinstance(records, list):
        raise ValueError("assessments must be a list")

    eligible = []
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("each assessment must be an object")
        timestamp = _validate_fields(record, ladders)
        if "run_id" in record:
            run_id = record["run_id"]
            if run_id in seen:
                raise ValueError(f"duplicate run_id: {run_id}")
            seen.add(run_id)
        if (all(key in record for key in _ASSESSMENT_FIELDS)
                and record["verified"]
                and all(record[key] == track[key] for key in _TRACK_FIELDS)):
            eligible.append((timestamp, record))
    # Stable sort preserves input array order for timestamp ties.
    eligible.sort(key=lambda item: item[0])
    window = [record for _, record in eligible[-5:]]
    average = sum(record["score"] for record in window) / 5 if len(window) == 5 else None

    selected = current
    if current not in supported:
        higher = [step for step in supported if step > current]
        if not higher:
            raise ValueError("current rung unavailable and no supported higher rung")
        selected, reason = higher[0], "context_floor_raised" if current < floor else "capability_fallback"
    elif average is None:
        reason = "insufficient_evidence"
    elif average <= 4.5:
        higher = [step for step in supported if step > current]
        selected, reason = (higher[0], "low_performance") if higher else (current, "ceiling_reached")
    elif all(record["score"] == 5 for record in window):
        lower = [step for step in supported if step < current]
        selected, reason = (lower[-1], "perfect_performance") if lower else (current, "floor_reached")
    else:
        reason = "performance_stable"
    family, effort = ladder[selected]
    return {
        "selected_step": selected,
        "selected_family": family,
        "selected_effort": effort,
        "reason": reason,
        "eligible_count": len(eligible),
        "excluded_count": len(records) - len(eligible),
        "window_run_ids": [record["run_id"] for record in window],
        "average": average,
        "reset_required": selected != current,
    }


def main(argv=None):
    """Read one JSON request and print one JSON recommendation."""
    arguments = sys.argv[1:] if argv is None else argv
    try:
        if len(arguments) != 1:
            raise ValueError("usage: python3 scripts/ladder.py REQUEST.json")
        request = json.loads(Path(arguments[0]).read_text(encoding="utf-8"))
        result = recommend(request)
    except (OSError, UnicodeError, ValueError) as error:
        print("error: " + " ".join(str(error).splitlines()), file=sys.stderr)
        return 1
    print(json.dumps(result, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
