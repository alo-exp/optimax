# Persistent controller and read-only calculator

Use Python 3 and the bundled `scripts/performance.py` for normal operation. The controller persists only the canonical per-user/project CSV, validates and replays its versioned events, and serializes updates using POSIX file locking. A host without the required filesystem/locking support must report that blocker rather than claim persisted continuity. The host supplies trusted identity/session values and authentic execution metadata; neither script authenticates those values or launches agents.

## Session and controller commands

Replace the example paths and identifiers with the canonical primary project root, the actual safe stable user ID established under [the policy](policy.md), and the host's trusted session ID. Do not copy a sample user identity into a real ledger. The bare `$optimax` invocation in Codex or `/optimax:optimax` in Claude Code maps to `on`; `off` and `status` map to the matching commands. Running `status` alone does not enable the policy.

```sh
python3 /path/to/optimax/scripts/performance.py --root /canonical/project --user ACTUAL_USER_ID --session TRUSTED_SESSION_ID --platform codex --complexity low on
python3 /path/to/optimax/scripts/performance.py --root /canonical/project --user ACTUAL_USER_ID --session TRUSTED_SESSION_ID status
python3 /path/to/optimax/scripts/performance.py --root /canonical/project --user ACTUAL_USER_ID --session TRUSTED_SESSION_ID adopt-policy
python3 /path/to/optimax/scripts/performance.py --root /canonical/project --user ACTUAL_USER_ID --session TRUSTED_SESSION_ID prepare /path/to/prepare.json
python3 /path/to/optimax/scripts/performance.py --root /canonical/project --user ACTUAL_USER_ID --session TRUSTED_SESSION_ID assess /path/to/assessment.json
python3 /path/to/optimax/scripts/performance.py --root /canonical/project --user ACTUAL_USER_ID --session TRUSTED_SESSION_ID off
```

For `on`, `--platform` accepts `claude` or `codex`, and `--complexity` accepts `low`, `medium`, `high`, or `super_high`. Supply the observed host and current task context. The response includes `orchestrator_suggestion` with `applied: false` and a `recommendations` list. Every explicit `on` returns it, including an idempotent call. Omitting platform returns both hosts' suggestions; omitting complexity discloses a conservative Medium assumption. These flags and returned suggestions never change model, effort, or native controls. The host renders the recommendation, or states that the selected pair already meets it.

To preserve a known or possibly active native configuration in the recommendation, pass `--platform codex --native-context '{"mode":"codex-ultra","active":true,"model_id":"CURRENT_MODEL_ID","effort":"CURRENT_EFFORT"}' on` (use `claude-ultracode` with `claude`). `active` is `true`, `false`, or `null` for unknown; true and unknown require the current nonempty model ID and effort. Active or unknown context retains the current pair in the recommendation and includes the ordinary recommendation as `baseline`; `applied` remains false. False returns the ordinary baseline with context. This is advice only: it does not activate, disable, or cancel native work.

`adopt-policy` takes no request file and records adoption of `optimal-ultra-ladder-v3` when needed. The first successful `prepare` also adopts atomically. Status and idempotent adoption do not fabricate a launch. V3 starts fresh Advisor windows while preserving compatible unchanged Executor v2 epochs/windows. Frozen v1/v2 registries retain historical event meaning. Policy adoption and CSV schema upgrade are distinct; see [the policy](policy.md).

An example preparation request for a low-complexity Codex Executor is:

```json
{
  "platform": "codex",
  "role": "executor",
  "tier": "low",
  "models": {"terra": "gpt-6.1-terra", "sol": "gpt-6.1-sol"},
  "available_steps": [0, 1, 2, 3, 4, 5, 6],
  "mode": "direct"
}
```

The Advisor has one performance track per platform and no complexity tier. Omit `tier` (or supply `null`) and specify the consultation's `advice_level`, for example:

```json
{
  "platform": "codex",
  "role": "advisor",
  "advice_level": "medium",
  "purpose": "planning",
  "complexity": "low",
  "models": {"sol": "gpt-6.1-sol", "astra": "gpt-6-astra"},
  "available_steps": [0, 1, 2],
  "mode": "direct"
}
```

A non-null Advisor tier is invalid. `advice_level` accepts `medium`, `high`, or `super_high` and defaults to `medium` when omitted for Advisor preparation. Their context floors are rungs 0/1/2: Claude Opus Medium/High/XHigh and Codex Sol XHigh/Sol Max/Astra Max. Each preparation binds its level/floor to the run. Raising context enforces its floor; lowering context alone retains the current selected rung. Executor requests require their actual routing tier, with no new Super High Executor tier.

When known, pass `purpose` (`planning`, `design`, or `execution`), task/consultation `complexity`, and optional boolean `needed` to preparation so the shared consultation gate validates the request. Supplying a non-null complexity or `needed: true` requires a purpose; `needed` must always be an actual boolean, even when purpose is omitted. Low planning/design uses Medium advice; Low execution is blocked; other execution requires `needed: true`. An explicit advice level cannot lower the floor derived from context. The manual path with only `advice_level` and no task context remains valid for a trusted host that already established consultation need; the engine cannot infer or verify that need from advice level alone.

These IDs are dated examples, not capability discovery. Use the exact models and supported rung list actually verified for the host. For Claude use the corresponding `haiku`, `sonnet`, and `opus` model map. Mode is `direct`, `codex-ultra`, or `claude-ultracode`; it is attribution and never activates a host feature. Keep native feature activation, stage execution owner, and dispatch route as three separate facts; a direct fallback does not establish native integration. A preparation returns a flat reservation containing the stable `run_id`, `epoch`, `platform`, `role`, `family`, exact `model_id`, `effort`, and `mode`. Pass that reservation to the native dispatch adapter; the engine does not return tool-call arguments. Prepare once for each controllable actual run before launching it; opaque native workers are unscored and outside this preparation contract. Never treat a reservation as proof that execution happened.

After independently reviewing the actual output, submit the returned run ID and observed receipt, for example:

```json
{
  "run_id": "RUN_ID_RETURNED_BY_PREPARE",
  "score": 5,
  "effective_model_id": "gpt-6.1-terra",
  "effective_effort": "low",
  "execution_id": "DISTINCT_ACTUAL_RUNTIME_EXECUTION_ID",
  "verified": true
}
```

`verified: true` attests that the Orchestrator independently checked the output and actual receipt; the controller cannot perform that review. Keep the reviewed evidence and explanation in the required user-facing report. Invalid or mismatched settings are ineligible; do not change a receipt to fit the requested rung. Stable execution IDs distinguish actual runs from cached replay. Retried submission of the same assessment must not create a second eligible result.

`status` never writes the ledger. A supported schema 1 ledger remains unchanged on read; the next actual mutation atomically upgrades it to schema 2 with the explicit top-level Executor `tier` column. An idempotent on/off or repeated identical assessment/import does not force a write or upgrade. This preserves history without deriving missing role or complexity attribution.

A fresh session is disabled until explicitly enabled. While off, preparation and learning stop; prior evidence and in-flight work remain. Disabling invalidates pending learning from that session generation, including pre-off work finishing after re-enable. Re-enable for newly prepared runs rather than retroactively importing suspended work. See [native-mode integration](native-modes.md) for staged workflow operation and receipt boundaries.

## Session decision helpers

The pure [scripts/session_policy.py](../scripts/session_policy.py) module supplies two Python functions without invoking helpers or changing settings:

```python
from scripts.session_policy import advisor_context, orchestrator_recommendation

orchestrator_recommendation("codex", "low")
advisor_context("codex", "low", "planning")
advisor_context("codex", "medium", "execution", needed=True)
```

Run Python from the skill root when using that import. `orchestrator_recommendation(platform, complexity=None, native_context=None)` returns a recommendation and `applied: False`; a missing level includes its conservative Medium assumption. The optional native context uses the CLI facts above; active or unknown state preserves the supplied pair and nests the ordinary baseline. Omitting it retains the existing behavior and does not detect native state. The host must discover and supply the facts: use `active: null` for an inconclusive probe when the current pair is known. If that pair is unknown, disclose that a safe switch cannot be recommended and preserve settings; do not invent facts or treat an omitted context as inactive. `Engine.set_enabled` also accepts this optional context. The host displays it on **every explicit enabling invocation**, including idempotent `on`, and compares it with the selected Orchestrator. If already satisfied, state that; never apply settings automatically. Low maps to Claude Haiku XHigh or Codex Terra Medium; every other level maps to Claude Sonnet High or Codex Terra High.

`advisor_context(platform, complexity, purpose, needed=False)` accepts `planning`, `design`, or `execution`. Planning/design always return mandatory consultation, including Low with Medium advice baseline. Low execution disallows consultation even when `needed=True`; execution at Medium or above consults only when needed. Results include `required`, `allowed`, `consult`, `advice_level`, `starting_step`, `family`, and `effort`. Complexity here describes task/consultation context (`low`, `medium`, `high`, `super_high`, or `None`), not a score tier. `super_high` creates no Executor tier. `needed` must be a boolean; invalid inputs fail validation. These helpers make no runtime authentication or model-availability claim.

## Read-only calculator

`scripts/ladder.py` remains a pure recommendation helper with no dependencies, network calls, launches, settings changes, or persistent writes. The controller builds its attributed input from the ledger. For an isolated policy calculation, supply an existing JSON request and run:

```sh
python3 /path/to/optimax/scripts/ladder.py /path/to/request.json
```

The helper does not ingest either CSV schema directly. A standalone caller must build its request only from independently reviewed attributed records. A field saying `verified: true` is the caller's assertion, not verification performed by this script.

### Calculator request

This empty-history example selects the starting Codex Executor rung for a low-complexity assignment:

```json
{
  "policy_version": "optimal-ultra-ladder-v3",
  "track": {
    "platform": "codex",
    "role": "executor",
    "tier": "low",
    "step": 0,
    "model_id": "gpt-6.1-terra",
    "epoch": "session-42-executor-low-1"
  },
  "available_steps": [0, 1, 2, 3, 4, 5, 6],
  "assessments": []
}
```

- `policy_version`: top-level ladder registry selector. Use `optimal-ultra-ladder-v3` for current decisions; frozen v1/v2 remain available for historical validation. It defaults to current v3 when omitted. Never mix assessments from different role-policy lineages into one standalone request.
- `platform`: `claude` or `codex`.
- `role`: `executor` or `advisor`.
- `tier`: Executor uses its actual `low`, `medium`, or `high` tier, with `business_doc` retained where specified by policy. Advisor uses JSON `null`; it has one unpartitioned track per platform. The pure calculator requires the `tier` field, unlike the controller which permits omission for Advisor preparation.
- `step`: zero-based rung from the SKILL.md ladder, at or above the Executor tier's floor or Advisor consultation's context floor.
- `model_id`: exact, independently established runtime model identifier.
- `epoch`: attributable identifier for this visit to the rung with this exact version.
- `available_steps`: nonempty list of unique, supported rung indices. Discover support before calling; this script does not discover it.
- `assessments`: attributed records in original assessment append order, used to break equal-timestamp ties.

Every attributed assessment contains all six track fields above, plus:

```json
{
  "run_id": "executor-run-42",
  "timestamp": "2026-11-07T05:00:00Z",
  "platform": "codex",
  "role": "executor",
  "tier": "low",
  "step": 0,
  "model_id": "gpt-6.1-terra",
  "epoch": "session-42-executor-low-1",
  "score": 5,
  "verified": true
}
```

For an Advisor calculator request, set `role: "advisor"`, `tier: null`, and its own Advisor rung/model/epoch in both the current track and attributed assessments. Use Advisor availability indices `[0, 1, 2]` and top-level `advice_level: "medium"`, `"high"`, or `"super_high"` to enforce the consultation floor (default Medium). Supply that advice level explicitly for a non-Medium consultation floor. Keep advice level as consultation provenance rather than a score partition. Never reuse an Executor epoch or split the Advisor's shared window by advice level.

`step` denotes the actual effective model/effort rung, not merely the requested setting. Verify actual effort against the ladder when attributing a row. A requested Max run that actually used High is not a Max assessment. Unknown effective effort or version makes the record ineligible. The helper trusts the caller's attribution and does not derive a model family from opaque provider deployment identifiers.

Timestamps must be timezone-aware ISO 8601. Scores must be integers 0–5; booleans are rejected as scores. `verified` must be a boolean. Missing attribution fields and unverified records are excluded from windows. Malformed present values, duplicate run IDs, invalid track/rung combinations, and invalid availability lists are errors; fix the input rather than deleting inconvenient scores. Conflicting records cannot be silently deduplicated.

## Result and follow-through

The result includes `selected_step`, `selected_family`, `selected_effort`, `reason`, `eligible_count`, `excluded_count`, `window_run_ids`, `average`, and `reset_required`. Average is `null` until five eligible results exist. Eligible count includes all matching current-epoch records, while the window contains at most the newest five.

Reasons distinguish insufficient evidence, stable performance, performance-driven movement, a reached floor or ceiling, and capability fallback. A recommendation names a logical family/effort pair; resolve the exact available model version separately before launching. If `reset_required` is true, establish a fresh durable epoch **before** launching the selected rung; the persistent controller performs this when used normally. A later version change also requires a fresh epoch even if the numerical rung stays the same. The pure calculator never creates an epoch or changes state.

Invalid input produces a compact error on stderr and a nonzero exit. No available rung at or above a required upward fallback is a blocker. Do not turn a calculator error into a guessed launch.

Run the observable-behavior tests with:

```sh
python3 -m unittest discover -s tests -v
```
