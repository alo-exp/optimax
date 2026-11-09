"""Pure policy suggestions; no native settings or performance ledgers are changed."""


def _validate(platform, complexity):
    if not isinstance(platform, str) or platform not in ("claude", "codex"):
        raise ValueError("platform must be claude or codex")
    if complexity is not None and (
        not isinstance(complexity, str)
        or complexity not in ("low", "medium", "high", "super_high")
    ):
        raise ValueError("complexity must be low, medium, high, super_high, or None")


def _assumption(complexity):
    return {"assumption": "Missing complexity conservatively assumes medium."} if complexity is None else {}


def orchestrator_recommendation(platform, complexity=None, native_context=None):
    """Suggest settings without applying them, retaining explicitly supplied native context."""
    _validate(platform, complexity)
    low = complexity == "low"
    family = ("haiku" if low else "sonnet") if platform == "claude" else "terra"
    effort = ("xhigh" if platform == "claude" else "medium") if low else "high"
    baseline = {
        "family": family,
        "effort": effort,
        "reason": "Low-complexity orchestrator baseline." if low else "Medium-or-higher orchestrator baseline.",
        "applied": False,
        **_assumption(complexity),
    }
    if native_context is None:
        return baseline
    if not isinstance(native_context, dict) or set(native_context) - {"mode", "active", "model_id", "effort"}:
        raise ValueError("native_context must be an object with known fields")
    if native_context.get("mode") != {"codex": "codex-ultra", "claude": "claude-ultracode"}[platform]:
        raise ValueError("native_context mode must match platform")
    if "active" not in native_context or (native_context["active"] is not None and type(native_context["active"]) is not bool):
        raise ValueError("native_context active must be a boolean or null")
    if ("model_id" in native_context) != ("effort" in native_context):
        raise ValueError("native_context model_id and effort must be supplied together")
    for field in ("model_id", "effort"):
        value = native_context.get(field)
        if (field in native_context and (not isinstance(value, str) or not value.strip())) or (
            native_context["active"] is not False and field not in native_context
        ):
            raise ValueError("native_context requires nonempty model_id and effort for active or unknown state")
    context = dict(native_context)
    if context["active"] is False:
        return {**baseline, "native_context": context}
    state = "active" if context["active"] else "unknown"
    return {
        "model_id": context["model_id"], "effort": context["effort"],
        "reason": ("Retain the supplied current settings; native mode state is " + state
                   + ". The ordinary baseline is an alternative with different settings."),
        "native_context": context, "baseline": baseline, "applied": False,
    }


def advisor_context(platform, complexity, purpose, needed=False):
    """Describe advisory eligibility and the starting family/effort suggestion.

    Planning and design always require consultation, with low using the medium
    advice baseline. Execution permits consultation at medium or above only,
    and consults when needed is True. None assumes medium. needed must be bool.
    Invalid arguments raise ValueError. Results are fresh dictionaries.
    No advisor is invoked; advisor steps are not performance complexity tiers.
    """
    _validate(platform, complexity)
    if not isinstance(purpose, str) or purpose not in ("planning", "design", "execution"):
        raise ValueError("purpose must be planning, design, or execution")
    if type(needed) is not bool:
        raise ValueError("needed must be a boolean")
    required = purpose in ("planning", "design")
    allowed = required or complexity != "low"
    advice_level = "medium" if complexity in (None, "low") else complexity
    step = ("medium", "high", "super_high").index(advice_level)
    ladder = (
        (("opus", "medium"), ("opus", "high"), ("opus", "xhigh"))
        if platform == "claude"
        else (("sol", "xhigh"), ("sol", "max"), ("astra", "max"))
    )
    family, effort = ladder[step]
    return {
        "required": required,
        "allowed": allowed,
        "consult": required or (allowed and needed),
        "advice_level": advice_level,
        "starting_step": step,
        "family": family,
        "effort": effort,
        **_assumption(complexity),
    }


SUBSTANTIVE_ACTIVITIES = (
    "code", "test_authoring", "test_work", "research", "documentation",
    "release_preparation", "semantic_integration",
)
ROOT_ACTIVITIES = ("coordination", "source_inspection", "independent_verification", "acceptance")


def execution_contract(enabled):
    """Describe the current mode; host snapshots and exceptions remain host claims."""
    if type(enabled) is not bool:
        raise ValueError("enabled must be an explicit boolean from current session status")
    return {
        "enabled": enabled,
        "substantive_owner": "executor" if enabled else "governing_host_policy",
        "root_execution": "listed_coordination_and_verification" if enabled else "governing_host_policy",
        "root_activities": list(ROOT_ACTIVITIES),
        "substantive_activities": list(SUBSTANTIVE_ACTIVITIES),
        "advisor_authorizes_execution": False,
        "automatic_root_fallback": False,
        "blanket_root_permission": False,
        "ownership_evidence": "declared_host_snapshot",
        "provider_verified": False,
        "learning_eligible": False,
    }
