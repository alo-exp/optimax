"""Prepare calls; never invoke tools or change orchestrator configuration.

Python API: prepare_dispatch(reservation, brief, route, capabilities).
CLI: python3 scripts/native_dispatch.py request.json, where request contains those
four named values. Prints one dispatch object; invalid input exits 2.

Capabilities must be copied from the actual installed tool schema and contain
schema_verified=True, tool, allowed_arguments, required_arguments, argument_map
(model/effort/prompt plus fork for Codex), supported_models, supported_efforts.
Optional model_aliases map exact requested IDs to supported Claude aliases.
Optional static_arguments supply other required fields such as task_name.
Direct routes require supported requested model/effort controls, not post-run
effective-setting evidence. Optional effective_model_id/effective_effort assertions
must not conflict with the reservation; the legacy effective_settings_verified
flag is accepted but does not attest execution. Preparation always records
effective_settings_verified=False and invents no effective identity. Independent
native evidence is still required for a learning receipt. Workflow stage
integration is not implemented.
"""
import copy
import json
from pathlib import Path
import sys


def _error(message):
    return ValueError(message + "; use a supported direct-agent route with explicit model and effort")


def _string(value, label):
    if not isinstance(value, str) or not value.strip():
        raise _error(label + " must be a nonempty string")
    return value


def _strings(value, label):
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise _error(label + " must be a list of nonempty strings")
    if len(value) != len(set(value)):
        raise _error(label + " must contain distinct values")
    return set(value)


def _identity(reservation):
    if not isinstance(reservation, dict):
        raise _error("reservation must be an object")
    fields = ("run_id", "epoch", "platform", "role", "family", "model_id", "effort", "mode")
    result = {key: _string(reservation.get(key), key) for key in fields}
    if result["platform"] not in ("codex", "claude"):
        raise _error("unsupported platform")
    if result["role"] not in ("executor", "advisor"):
        raise _error("unsupported role")
    modes = {"codex": ("direct", "codex-ultra"), "claude": ("direct", "claude-ultracode")}
    if result["mode"] not in modes[result["platform"]]:
        raise _error("unsupported mode for platform")
    return result


def _argument_schema(route, capabilities):
    if not isinstance(capabilities, dict) or capabilities.get("schema_verified") is not True:
        raise _error("a verified actual tool schema is required")
    tool = _string(capabilities.get("tool"), "tool")
    allowed = _strings(capabilities.get("allowed_arguments"), "allowed_arguments")
    required = _strings(capabilities.get("required_arguments"), "required_arguments")
    if not required <= allowed:
        raise _error("required_arguments must be allowed by the schema")
    mapping = capabilities.get("argument_map")
    if not isinstance(mapping, dict):
        raise _error("argument_map must explicitly map model, effort and prompt")
    semantics = {"model", "effort", "prompt", "fork"} if route == "codex-spawn" else {"model", "effort", "prompt"}
    if set(mapping) != semantics:
        raise _error("argument_map must explicitly map model, effort, prompt and any required fork")
    for semantic, argument in mapping.items():
        _string(argument, semantic + " argument")
    if len(set(mapping.values())) != len(mapping):
        raise _error("argument_map fields must be distinct")
    for semantic, argument in mapping.items():
        if argument not in allowed:
            raise _error(semantic + " argument is not supported by the actual schema")
    if route == "codex-spawn" and mapping != dict(model="model", effort="reasoning_effort", prompt="message", fork="fork_turns"):
        raise _error("Codex requires exact model/reasoning_effort/message/fork_turns arguments")
    return tool, allowed, required, mapping


def _selected_model(identity, route, capabilities):
    aliases = capabilities.get("model_aliases", {})
    if not isinstance(aliases, dict):
        raise _error("model_aliases must be an object")
    for exact, alias in aliases.items():
        _string(exact, "exact model ID")
        _string(alias, "model alias")
    if route == "codex-spawn" and aliases:
        raise _error("Codex model aliases are unsupported; exact model override is required")
    selected = aliases.get(identity["model_id"], identity["model_id"])
    if selected not in _strings(capabilities.get("supported_models"), "supported_models"):
        raise _error("requested model is not declared supported by the actual schema")
    if identity["effort"] not in _strings(capabilities.get("supported_efforts"), "supported_efforts"):
        raise _error("requested effort is not declared supported by the actual schema")
    return selected


def prepare_dispatch(reservation, brief, route, capabilities):
    """Return route/tool/arguments/provenance, or raise ValueError with fallback.

    This is read-only preparation. schema_verified is a caller assertion about
    installed capabilities, not evidence that any native call has executed.
    """
    identity = _identity(reservation)
    _string(brief, "brief")
    routes = {"codex-spawn": "codex", "claude-agent": "claude", "claude-workflow": "claude"}
    if not isinstance(route, str) or route not in routes:
        raise _error("unsupported route")
    if route == "claude-workflow":
        raise _error("claude-workflow is unsupported: official WorkflowInput uses script, name, scriptPath, args, resumeFromRunId, title and description, not model/effort/prompt; workflow stages require separate verified host integration")
    if routes[route] != identity["platform"]:
        raise _error("route does not match reservation platform")
    tool, allowed, required, mapping = _argument_schema(route, capabilities)
    selected_model = _selected_model(identity, route, capabilities)
    if ("effective_settings_verified" in capabilities
            and type(capabilities["effective_settings_verified"]) is not bool):
        raise _error("effective_settings_verified must be a boolean when provided")
    for field, expected in (("effective_model_id", identity["model_id"]),
                            ("effective_effort", identity["effort"])):
        if capabilities.get(field) is not None and capabilities[field] != expected:
            raise _error(field + " conflicts with reservation")
    provenance = {
        "run_id": identity["run_id"], "epoch": identity["epoch"], "role": identity["role"],
        "requested_model_id": identity["model_id"], "requested_effort": identity["effort"],
        "effective_settings_verified": False,
    }
    fence = ("Root-owned leaf fence: root owns enable/off, Advisor consultation, WBS expansion, "
             "dispatch, and the runtime ledger. Do not let inherited skills trigger their own scheduler. ")
    if identity["role"] == "executor":
        fence += "Do the assigned task; no recursive delegation and no Advisor consultation; request scope or replan from root."
    else:
        fence += "Provide read-only advice; no implementation, no mutations, and no recursive Advisor consultation."
    prompt = ("Execution reservation (preserve for the execution receipt):\n"
              + json.dumps(provenance, sort_keys=True) + "\n\n" + fence + "\n\nTask brief:\n" + brief)
    arguments = capabilities.get("static_arguments", {})
    if not isinstance(arguments, dict):
        raise _error("static_arguments must be an object")
    if not set(arguments) <= allowed:
        raise _error("static_arguments contain unsupported fields")
    if set(arguments) & set(mapping.values()):
        raise _error("static_arguments cannot override selected model, effort, prompt or fork")
    try:
        json.dumps(arguments, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise _error("static_arguments must be JSON values") from exc
    arguments = copy.deepcopy(arguments)
    arguments[mapping["model"]] = selected_model
    arguments[mapping["effort"]] = identity["effort"]
    arguments[mapping["prompt"]] = prompt
    if route == "codex-spawn":
        arguments["fork_turns"] = "none"
    if not required <= set(arguments):
        raise _error("required tool arguments are missing: " + ", ".join(sorted(required - set(arguments))))
    return dict(route=route, tool=tool, arguments=arguments, provenance=provenance)


def validate_receipt(reservation, receipt):
    """Check reported identity consistency; this does not authenticate execution.

    The caller must independently establish the effective model, effort and
    execution ID from native evidence. Durable deduplication belongs to the ledger.
    """
    identity = _identity(reservation)
    if not isinstance(receipt, dict):
        raise _error("receipt must be an object")
    expected = {
        "run_id": identity["run_id"], "epoch": identity["epoch"],
        "requested_model_id": identity["model_id"], "requested_effort": identity["effort"],
        "effective_model_id": identity["model_id"], "effective_effort": identity["effort"],
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise _error("receipt " + key + " does not match reservation")
    _string(receipt.get("execution_id"), "receipt execution_id")
    return copy.deepcopy(receipt)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        if len(argv) != 1:
            raise ValueError("usage: native_dispatch.py request.json")
        request = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
        if not isinstance(request, dict) or set(request) != {"reservation", "brief", "route", "capabilities"}:
            raise ValueError("request must contain exactly reservation, brief, route, capabilities")
        print(json.dumps(prepare_dispatch(**request), sort_keys=True, allow_nan=False))
        return 0
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
