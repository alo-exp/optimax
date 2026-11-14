# Persistent controller and read-only calculator

Use Python 3 and the bundled `scripts/performance.py` for normal operation. The controller persists the canonical per-user/project CSV, validates and replays its versioned events, and serializes updates using POSIX `flock` on the project directory, or on Windows `msvcrt` locking of a per-project file at `~/.optimax/locks/<project-hash>.lock` outside the project. Windows controllers for a project must share the same resolved user profile on a local filesystem with a writable profile cache. Different temporary-directory environments do not change the lock namespace. Lock files remain after use; do not remove them while controllers may be active. An unavailable cache fails without a temporary-directory fallback or ledger mutation. Lock contention is retried; other locking errors are reported. A host without the required filesystem/locking support must report that blocker rather than claim persisted continuity. The host supplies trusted identity/session values and authentic execution metadata; neither script authenticates those values or launches agents.

The locks coordinate cooperating controllers; all ledger writers must use the same shared lock. Keep the ledger itself, project root, its ancestors, and the ledger directory stable while a controller runs. Replacing an existing ledger is not an atomic replace-if-unchanged operation: a replacement by a noncooperating writer can be overwritten. Pinned POSIX descriptors keep publication anchored to the opened directory; identity checks before and after publication detect observed movement, including movement during publication or synchronization, but cannot prevent movement after the final observation. A binding error after publication can leave complete updated history in the moved original object while a replacement path remains unchanged. Locate and independently verify that original history before recovery; `status` on an empty replacement project is not proof of recovery. The controller does not delete or roll back published history when reporting such an error.

The controller preserves the parent interpreter's `csv.field_size_limit`, including when imported or used alongside unrelated CSV readers. It first parses with the parent's strict `DictReader`. On `csv.Error`, it discards the partial parse, rewinds the same already-open guarded ledger stream, and passes that descriptor as stdin to fixed stdlib-only code in an isolated `sys.executable -I` child with `shell=False`; it never reopens the ledger pathname. Only the child configures a larger parser limit. Header, schema, identity and event-replay validation remain in the parent. A helper startup, parse or response error fails without changing the ledger.

The writer and isolated codec share a private decoded-character ceiling: the smaller of `sys.maxsize` and the platform's signed C-long maximum, supporting older Python codecs as well as newer ones. Every header and serialized event field is checked before final publication. CSV quote expansion and UTF-8 byte length do not count, while JSON escape characters stored inside `data` do count. A field over the private ceiling raises `ValueError`, preserves the original ledger, and removes the pending file. The caller's mutable global CSV limit does not change this write bound.

The fallback adds process startup and serialization work only after a CSV parse error. It requires a runnable matching Python executable, stdlib modules, and permission to spawn a process with the opened file as stdin. It retains the existing lock and directory guard until reading completes. It holds parsed rows and the helper response in memory; available memory and OS resource policy bound large histories. There is no arbitrary helper timeout. Cancellation kills and waits for the child before propagating the interruption and closing the guarded stream. POSIX descriptor anchoring and cancellation are tested; native Windows process/handle behavior remains unqualified.

`Engine.import_history` accepts a list of JSON objects and requires string keys in every nested object, including objects inside arrays or tuples. Non-string keys raise `ValueError` before any mutation; the API does not coerce numeric, boolean, or null keys to strings or merge colliding keys. This tightens the Python API compatibility contract for inputs that older versions sometimes accepted through JSON key coercion. Normal CLI JSON objects already have string keys. Non-finite numbers and circular references remain rejected. Previously persisted valid history keeps its original digest and bytes, including compatible old records whose stored keys are already strings; damaged digests remain errors. Accepted string-key payload serialization and the private CSV size ceiling are unchanged.

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

### Project relocation

When a project is deliberately moved, the ledger remains bound to its previously recorded canonical path and ordinary commands fail closed. First independently verify the old and new project identities and ensure all controllers using the old location have stopped. Run the current controller against the new canonical root with `relocate /path/to/relocation.json`, where the request is `{"from_root":"/verified/previous/canonical/root"}`. The operation validates the existing ledger and appends the old-to-new binding without rewriting prior events. A wrong origin or damaged history fails without changing the ledger. Use a controller version that understands relocation events afterward; older versions cannot read the relocated ledger. The command does not establish that a copied project is the same project: the operator must verify that fact before requesting it.

A relocation error after publication can leave the new binding visible with durability unconfirmed. Inspect `status` at the independently verified new root; status is not durability proof. If the new binding is already recorded, repeating relocation with the old origin correctly rejects it. To confirm the POSIX namespace without rewriting history, use `adopt-policy` only when status shows the policy is already current, or repeat unchanged `on`/`off` for a known existing session. These operations must succeed in syncing the ledger directory before acknowledging success. If status fails or the binding does not match the verified move, reverify project identity and origin instead of guessing another origin. This recovery does not provide POSIX directory-sync durability on Windows.

For `on`, `--platform` accepts `claude` or `codex`, and `--complexity` accepts `low`, `medium`, `high`, or `super_high`. Supply the observed host and current task context. The response includes `orchestrator_suggestion` with `applied: false` and a `recommendations` list. Every explicit `on` returns it, including an idempotent call. Omitting platform returns both hosts' suggestions; omitting complexity discloses a conservative Medium assumption. These flags and returned suggestions never change model, effort, or native controls. The host renders the recommendation, or states that the selected pair already meets it.

To preserve a known or possibly active native configuration in the recommendation, pass `--platform codex --native-context '{"mode":"codex-ultra","active":true,"model_id":"CURRENT_MODEL_ID","effort":"CURRENT_EFFORT"}' on` (use `claude-ultracode` with `claude`). `active` is `true`, `false`, or `null` for unknown; true and unknown require the current nonempty model ID and effort. Active or unknown context retains the current pair in the recommendation and includes the ordinary recommendation as `baseline`; `applied` remains false. False returns the ordinary baseline with context. This is advice only: it does not activate, disable, or cancel native work.

### Instruction audit on activation

Every explicit `on`, including an idempotent call, performs a fresh bounded read of instruction candidates and returns `instruction_audit`: `candidates` identify path, scope and read status; `findings` identify path, scope, category, line and excerpt; `coverage` reports `complete: false` and gaps; and `host_confirmed_loaded` contains only host assertions. Supply the actual platform and optional `--instruction-context` JSON with host-known facts. Its optional `cwd` must equal the actual working directory; `host_confirmed_loaded`, `codex_fallback_names`, and `codex_max_bytes` are caller claims subject to helper bounds, not independently authenticated host state. The Python controller accepts `instruction_context` on `Engine.set_enabled`. `status` and `off` do no instruction-audit I/O and do not alter the ledger for an audit.

The standalone read-only `scripts/instruction_audit.py --platform codex|claude` accepts the same optional `--instruction-context` JSON and can be run even when enabling the ledger fails. It provides bounded conventional discovery, not an exhaustive host-loader trace: Codex checks global candidates and project candidates from the nearest Git root to the current directory, including override and caller-supplied fallback names. If no Git root is found, it checks the current directory and reports a gap. The supplied Codex byte cap applies to Codex candidates, not Claude candidates. Claude checks conventional global and local `CLAUDE.md`, `CLAUDE.local.md`, and `AGENTS.md` candidates. Safe directory and file traversal is required; when the platform lacks the necessary primitives, affected sources remain unreviewed and coverage reports a gap. Host settings determine which files actually apply; rules, imports, managed instructions, unknown configuration and other host behavior can create gaps. A candidate is not proof it was loaded, and no regex hits do not establish compatibility.

The host must semantically review potential fixed helper model or effort, delegation or Advisor restrictions, and assessment, storage or performance-policy evidence against governing priority, scope and later conversation. Disclose conflicts and block only affected work while continuing authorized independent work; never infer permission for root fallback. Do not edit instructions, change models, add an approval gate, install hooks, or claim automatic interception as a consequence of the audit.

`adopt-policy` takes no request file and records adoption of `optimal-ultra-ladder-v4` when needed. The first successful `prepare` also adopts atomically. Status and idempotent adoption do not fabricate a launch. Adoption proceeds in order through v2 and v3 to v4. V4 preserves compatible Executor and Codex Advisor lineage/windows; Claude Advisor starts a fresh selection and epoch at the next consultation floor, retaining historical events and excluding late old-lineage receipts. Policy adoption and CSV schema upgrade are distinct; see [the policy](policy.md).

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

These IDs are dated examples, not capability discovery. Use the exact models and supported rung list actually verified for the host. For Claude use the corresponding `haiku`, `sonnet`, and `opus` model map. Mode is `direct`, `codex-ultra`, or `claude-ultracode`; it is attribution and never activates a host feature. Keep native feature activation, stage execution owner, and dispatch route as three separate facts; a direct fallback does not establish native integration. A preparation returns a flat reservation containing the stable `run_id`, `epoch`, `platform`, `role`, `family`, exact `model_id`, `effort`, and `mode`. Pass that reservation to the native dispatch adapter; the engine does not return tool-call arguments. Prepare once for each adaptive controllable run before dispatch; use the limited fixed-review path below when the controller cannot represent a user-directed review rung. Opaque native workers are unscored and outside this preparation contract. Never treat a reservation as proof that execution happened.

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

Both the Python `Engine.assess` API and CLI assessment request require an explicit boolean `verified`. Omitting it rejects the request before recording an assessment or changing the ledger, leaving the run available for a corrected submission. Explicit `false` records an unverified, ineligible historical outcome; use `true` only after the independent review described above.

`status` never writes the ledger. A supported schema 1 ledger remains unchanged on read; the next actual mutation atomically upgrades it to schema 2 with the explicit top-level Executor `tier` column. An idempotent on/off or repeated identical assessment/import does not force a write or upgrade. This preserves history without deriving missing role or complexity attribution.

On POSIX, successful mutations confirm the ledger directory namespace with `fsync` while holding the transaction lock and directory guard. An error after publication can leave a complete, readable ledger whose durability is unconfirmed; the controller preserves that visible history. Retrying unchanged on/off, an identical assessment, policy adoption, or a duplicate import attempts the directory sync before reporting success without rewriting rows. `status` performs no sync and is not durability confirmation. These barriers do not establish power-loss guarantees for every filesystem, and the Windows branch does not provide this POSIX directory-sync durability confirmation.

On POSIX first publication, the pending name is hard-linked to the canonical ledger, the directory is synced, and the pending name is then unlinked. Filesystem crash semantics can leave or revive a temporary `.pending` name. It initially shares the first published inode, but later canonical replacements can leave it pointing to an older, stale snapshot; it is not a second ledger authority. An interruption earlier in staging can also leave residue. The controller reads only the canonical filename. This is a possible filesystem-semantics limitation, not an observed crash outcome or a guarantee about recovery.

A fresh session is disabled until explicitly enabled. While off, preparation and learning stop; prior evidence and in-flight work remain. Disabling invalidates pending learning from that session generation, including pre-off work finishing after re-enable. Re-enable for newly prepared runs rather than retroactively importing suspended work. See [native-mode integration](native-modes.md) for staged workflow operation and receipt boundaries.

## Execution contract and visible checkpoint

The `on`, `status`, and `off` responses include `execution_contract`. Enabled mode requires an Executor for substantive code, test authoring, research, documentation, release preparation and semantic integration. The listed root activities cover coordination, source inspection, independent verification and acceptance. `advisor_authorizes_execution`, `automatic_root_fallback`, `blanket_root_permission`, `provider_verified`, and `learning_eligible` are false. Off mode defers to governing host policy; it grants no blanket root authority. This contract describes policy and does not authenticate actual assignments.

Before substantive work, material phase changes, resume/compaction, late correction and acceptance, show an actual host-returned Executor assignment or a concrete blocker/permitted explicit exception. A controller reservation or Advisor consultation alone is insufficient. Use the optional task `execution` metadata and explicit `enabled` boolean in [the readiness helper](parallel-execution.md) to validate the supplied checkpoint snapshot. Its CLI accepts stdin JSON and returns `execution_checkpoints`; the host must invoke it and enforce the decision. No installed hook or universal tool interception is claimed. Optional `root_start_authorized` in that snapshot records authorization when `root_started` work began, using exactly true/false/null (omitted means unknown). Current exceptions and off mode do not rewrite prior known or unknown history; prior authorization does not grant current permission. See the readiness reference for the separate `deviation` and current `execution_allowed` semantics.

Schema-checked supported requested controls permit dispatch without an effective runtime receipt. Record the actual assignment ID and requested-only pair; retain useful output for independent review, but do not submit fabricated effective fields or an eligible assessment. Only a genuine matching receipt plus independent acceptance permits model-specific learning. Known precedence conflicts or unsupported selection fields remain capability blockers.

## Fixed-review and dispatch limits

The legacy `launch` event is a reservation created by `prepare`, not proof that a helper was dispatched or ran. Preserve that historical event meaning and the adaptive ledger; the controller does not record host dispatch confirmation, failure, or cancellation. Unused reservations remain unused. Record a failed, uncertain, or cancelled dispatch truthfully in the ordinary durable task/review report, using the actual host result and assignment ID when one exists; if none was returned, say so. Do not invent an event or assessment, fabricate receipts, edit ledger rows, or describe an unavailable failure/cancellation protocol.

A fixed user-directed review can require a rung that differs from adaptive selection, including an authorized extra rung. The controller has no fixed-rung override. Apply exactly these two branches:

1. With the policy enabled and a valid matching pre-dispatch adaptive reservation for this actual review assignment, retain that reservation and follow all existing eligibility rules: genuine matching effective receipt, independent output review, distinct actual execution ID, valid session generation and policy lineage/epoch. A fixed review that coincides with adaptive selection is not excluded merely because its rung was user-directed; eligibility is not automatic.
2. Without a valid matching reservation, or when the policy is off, an otherwise user-authorized fixed review uses supported host dispatch and the ordinary durable review report only. This is report-only execution: no adaptive assessment even with a later receipt. Do not prepare a different selection as a proxy, change availability to force it, relabel the task tier, or enable policy merely to run the fixed review. Record the actual host assignment ID (or explicitly no returned ID), requested model/effort, candidate, scope, pass and dispatch outcome, plus the independently reviewed result. State provider-effective settings as unknown when no genuine receipt is available. There is no controller run ID or epoch for this branch; use an ordinary report label if needed, never an invented controller ID or epoch. Never attach a mismatched reservation to that review or submit a score for it. Preserve the adaptive track and existing ledger history.

An unsupported fixed rung blocks that rung: no upward substitution, silent skip, or fabricated coverage. A compatible supported direct route may request the same fixed pair without changing native controls. Adaptive upward capability fallback applies only to adaptive selection, never the fixed review sequence. The ordinary report is execution/review evidence, not another score store; requested-versus-effective coverage obligations remain unchanged.

## Session decision helpers

The pure [scripts/session_policy.py](../scripts/session_policy.py) module supplies decision helpers without invoking helpers or changing settings:

```python
from scripts.session_policy import advisor_context, execution_contract, orchestrator_recommendation

orchestrator_recommendation("codex", "low")
advisor_context("codex", "low", "planning")
advisor_context("codex", "medium", "execution", needed=True)
execution_contract(enabled=True)
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
  "policy_version": "optimal-ultra-ladder-v4",
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

- `policy_version`: top-level ladder registry selector. Use `optimal-ultra-ladder-v4` for current decisions; frozen v1/v2/v3 remain available for historical validation. It defaults to current v4 when omitted. Never mix assessments from different role-policy lineages into one standalone request.
- `platform`: `claude` or `codex`.
- `role`: `executor` or `advisor`.
- `tier`: Executor uses its actual `low`, `medium`, or `high` tier, with `business_doc` retained where specified by policy. Advisor uses JSON `null`; it has one unpartitioned track per platform. The pure calculator requires the `tier` field, unlike the controller which permits omission for Advisor preparation.
- `step`: the actual recorded zero-based rung from the applicable SKILL.md ladder, not a pre-raised selection. An Executor step must meet its tier floor. For a v3/v4 Advisor, the actual step may be below a newly raised consultation floor: the calculator selects the lowest supported rung at or above that floor, returns `context_floor_raised`, and requires a reset. If the current rung is unavailable at or above the floor, it selects the next supported higher rung as `capability_fallback`. It raises an error if no supported rung meets the floor, or if an unavailable current rung has no supported higher rung; it does not substitute downward.
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

For an Advisor calculator request, set `role: "advisor"`, `tier: null`, and its own Advisor rung/model/epoch in both the current track and attributed assessments. Supply supported Advisor availability indices discovered on the host (Claude can include `[0, 1, 2, 3]`; Codex can include `[0, 1, 2]`) and top-level `advice_level: "medium"`, `"high"`, or `"super_high"` to enforce the consultation floor (default Medium). Supply that advice level explicitly for a non-Medium consultation floor. Keep advice level as consultation provenance rather than a score partition. Never reuse an Executor epoch or split the Advisor's shared window by advice level.

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
