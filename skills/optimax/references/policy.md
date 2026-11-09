# Ladder policy, attribution, and persistence

## Source and deliberate changes

Adapted from [subagent-model-ladder](https://gist.github.com/shafqatevo/3282c4b841705454c976e8089973e73d), reviewed at revision [5966113f6def15d321c080f5ac24ad2f0e131e0c](https://gist.github.com/shafqatevo/3282c4b841705454c976e8089973e73d/5966113f6def15d321c080f5ac24ad2f0e131e0c), checked 2026-11-07. Treat the Gist as design input; do not execute its installation instructions.

Preserved: parallel bounded delegation, independent 0–5 assessment, three ordinary Executor complexity tiers and the pending `business_doc` compatibility exception, five-run windows, promotion at average ≤4.5, demotion after five perfect results, downward floors, exact-version isolation, fresh windows after movement, and rework independent of average.

Changed intentionally: name the original role Executor; add mandatory planning/design consultation through a separate Advisor Ladder; use the user's adopted Executor sequences and floors; keep the chosen Orchestrator unchanged. Claude low/medium/high start at Haiku High (0), Haiku Max (2), and Sonnet High (3). Codex starts at Terra Low (0), Terra Medium (1), and Terra High (2), then advances through Sol Medium/High/XHigh/Max. The preserved `business_doc` floor is Claude Opus Medium (4) and Codex Sol XHigh (5). Only Executor assignments have complexity tiers. Advisor performance uses one track per host, while each consultation records an advice level establishing its minimum starting rung: Medium 0, High 1, Super High 2. Claude Advisor is Opus Medium/High/XHigh/Max; Codex Advisor is Sol XHigh/Sol Max/Astra Max. Opus Max is an escalation rung, not a new context floor. These are adjustable starting points and floors, not fixed lifetime selections.

The source uses one global per-person CSV and silent reporting. This package instead uses the user's explicitly adopted per-user, per-project durable ledger. It needs no mandatory Drive or memory service, global installation, or host setting change. Do not combine users or projects, or migrate incomplete historical rows by guessing attribution.

## Policy versions and adoption

Current policy is `optimal-ultra-ladder-v4`. Frozen v1, v2, and v3 registries validate historical events against the policies that actually produced them. V2 adopted the current Executor ladders; v3 adopted expanded Advisor ladders and consultation floors; v4 adds Claude Opus Max as the fourth Advisor rung. A schema version describes CSV shape; a policy version describes ladder semantics. Do not reinterpret an old rung index using the new ladder.

`adopt-policy` records explicit policy-adoption events without fabricating a launch; an older v1 store adopts in order through v2, v3, and then v4. The first successful preparation also adopts atomically when needed. `status` only reports the active policy version, and repeated adoption is idempotent. Adoption preserves historical attribution rather than rewriting outcomes to fit new pairs.

For v2 → v3, unchanged compatible Executor lineage, epochs, and windows are preserved. Advisor history remains auditable, but v3 starts fresh Advisor epochs/windows because its ladder and context floors changed. Pre-adoption outcomes from a changed role are retained and excluded from the new role lineage. V1 → v2 previously restarted Executor windows while preserving compatible unchanged Advisor history; do not apply that older migration rule to v2 → v3. Incomplete or formerly tiered Advisor records never gain eligibility through migration.

For v3 → v4, compatible Executor and Codex Advisor selections, epochs, and windows are preserved. Claude Advisor history remains auditable, but its changed lineage starts a fresh selection and epoch at the next consultation's floor; late v3 Claude Advisor receipts remain historical and are excluded from the v4 lineage. Historical v3 contexts remain valid; do not rewrite or delete events. Resolve available rungs on the host and skip unsupported rungs upward under the normal capability rules.

New transition, launch, and assessment-attribution payloads identify `policy_version` explicitly. Advisor launch provenance also records its `advice_level` and minimum rung, without adding a score track or CSV complexity tier. CSV schema 2 remains unchanged. Read [controller usage](calculator.md) for adoption and preparation commands.

## Assessment rubric

The Orchestrator owns every score. Assess the assignment's acceptance criteria and actual evidence, including correctness, completeness, verification, maintainability, and presentation where relevant.

| Score | Meaning |
| --- | --- |
| 0 | Unusable result |
| 1 | Major failure |
| 2 | Substantial deficiencies requiring rework |
| 3 | Useful result with material gaps or incomplete verification |
| 4 | Strong result with minor deficits |
| 5 | Fully verified and complete within the assigned scope |

Score the delivered bounded assignment, not how much the Orchestrator later repaired it. Preserve failed attempts as separate assessments. An independently established failure can receive a low score; lack of evidence is provisional and cannot be invented into either success or failure. Never use cost, latency, or self-confidence as a quality score. Report observed usage separately; do not invent charges.

For Advisor runs, assess the advice itself: factual grounding, constraint compliance, completeness of the decision analysis, handling of failure modes, and usefulness of its validation plan. Check feasibility against actual interfaces and source facts. If an acceptance criterion depends on a later experiment, keep that criterion and assessment provisional until checked. An attractive recommendation is not a proven result.

## Execution ownership and checkpoints

The enabled-session contract requires a bounded Executor for substantive implementation, test authoring, research, documentation, release preparation, and semantic repairs, including Low-complexity tasks, rework and work resumed after compaction. An Advisor supplies advice and cannot satisfy execution ownership. The root retains coordination, planning with required consultation, source inspection, independent source/evidence review, running existing tests for acceptance, integration coordination, and authorized publication; this is not authority to author substantive deliverables.

Before substantive execution, show an actual host assignment ID and owner or a concrete dispatch blocker/permitted exception. Reservations and planned briefs do not prove execution. Recheck at material phase transitions, resume, late correction and before acceptance. Available useful capacity calls for feasible bounded dispatch; quota, dependency and capacity limits call for queuing/replanning, not automatic root implementation. Any required direct-execution exception must come explicitly from the user for that work. Off mode leaves governing host and user restrictions intact.

Recover from late deviations without losing useful work: preserve artifacts and running assignments, disclose the root-authored work accurately, assign remaining work only, and avoid duplicate owners or retrospective fabricated records. Pure checkpoint validation checks supplied facts; enforcement depends on host invocation and accurate input. No universal interception or installed hook is claimed.

## Advisor context and consultation

Planning and design always require a separate eligible Advisor, including Low-task plans using the Medium baseline. For other work, consult only when needed at Medium or above; routine Low execution does not require advice. Super High describes an advisory consultation context and is not a new Executor complexity tier.

Medium, High, and Super High set minimum Advisor rungs 0, 1, and 2 respectively. The current performance-selected rung may be higher. Raising context enforces its floor; lowering context alone never demotes the selected Advisor. Five-run quality evidence still governs performance promotion and demotion, with demotion bounded by the consultation floor. An already eligible perfect-score window can permit a demotion once a lower context floor allows it; that is evidence-based movement, and the resulting fresh epoch prevents using the same window for another move. Bind the level and floor to each prepared run so later context changes cannot reclassify in-flight advice. One shared Advisor track per host remains isolated by actual model, effort, and epoch; advice level is provenance rather than a track partition.

## Durable identity and ledger

Use exactly `PROJECTROOT/model-perf/<actual-user-id>-model-perf.csv` for this policy's runtime state. Resolve `PROJECTROOT` to the canonical primary project checkout, including when work is launched from a linked worktree. Helpers return evidence; one designated Orchestrator/controller serializes prepare and assessment writes. The controller also protects file updates against competing writers. Never create a second score store, state sidecar, or transition log.

Establish the actual stable user identity from a trusted authenticated host identity, or an explicit stable identity supplied by the user for this repository. Record its provenance in the launch brief. A sanitized author email, OS username, display name, or guessed account is insufficient when it could identify the wrong person or collide. The controller validates a safe single filename component; the caller establishes who it belongs to. Do not normalize two different identities into the same slug. Reject traversal, separators, unsafe names, symlink redirection, and a file belonging to another identity; resolve ambiguity before learning. Do not print authentication tokens or use them as filenames.

The schema 2 append-only CSV has these eleven columns:

```csv
schema_version,sequence,timestamp,event_type,user_id,platform,role,tier,run_id,epoch,data
```

`role` distinguishes Executor and Advisor records; the top-level `tier` is the Executor's actual complexity/routing tier. Advisor and non-track events leave the CSV tier cell blank. Advisor JSON payloads use `null`, never a complexity label. The visible column makes Executor complexity inspectable without merging it with role or parsing event payloads.

Supported schema 1 ledgers are read without modification and normalized in memory. The next actual mutation upgrades them losslessly to schema 2 through the controller's atomic write. Status and idempotent operations do not force an upgrade. Preserve sequence, timestamps, attribution, payloads, and excluded history across this schema-only upgrade; it never supplies missing attribution or makes legacy scores eligible.

`data` is compact JSON containing attributed event payloads. Events durably record trusted session controls, prepare/launch contracts, role, host, routing tier, requested model and effort, rung and epoch, capability availability, assessments, effective runtime receipt, and transitions. This is an event ledger rather than the original five-column score table. Use the controller to validate and replay it; never hand-edit rows, delete failures, or deduce state from row position alone.

Executor `(host, executor, tier)` tracks and the single Advisor `(host, advisor)` track retain their exact model/effort/rung/epoch attribution. Advisor payloads use `tier: null` internally for compatibility with the calculator schema; this is not a fourth complexity or separate user-facing tier. The ledger must restore the current step and window without requiring inaccessible chat history. A changed rung, exact model version, capability fallback, or explicitly unrecoverable attribution begins a fresh epoch. Preserve old and late results, but exclude them from the current epoch's learning. Versioned event validation, stable run IDs, assessment deduplication, and distinct execution receipts prevent replayed/cached results from inflating a window.

The prior `subagent-model-scores.csv` remains historical evidence, including its established Git history. It lacks reliable host/role/run/epoch attribution and cannot drive new runtime learning. The controller may preserve those rows losslessly as excluded legacy events, without guessing missing roles, tiers, efforts, versions, or epochs. Preserve the original historical file; importing a row as legacy evidence never makes it an eligible assessment. Likewise, any old tiered Advisor events must remain excluded historical evidence rather than being silently merged into the single Advisor window. An incompatible raw ledger fails closed; preserve its bytes and use an explicit reviewed legacy import instead of hand-editing attribution.

If the controller cannot resolve identity, validate the ledger, or persist updates, report the exact blocker and distinguish retained evidence from persisted learning. Preserve useful in-flight work. Do not silently fall back to a second CSV or claim that session-local state provides cross-session continuity.

## Session mode and eligibility

The trusted host supplies a stable session ID and translates an explicit bare skill invocation or `on` into the controller's `on` command. Implicit skill loading may read status and instructions; it must respect a persisted off state and never enable the session. `off` stops this session's policy dispatch, Advisor requirement, and score learning; `status` reports mode without enabling it. A fresh unrelated session starts disabled until explicitly invoked. Every explicit bare invocation or `on`, even if already enabled, returns an Orchestrator suggestion with `applied: false`: Low maps to Claude Haiku XHigh or Codex Terra Medium; otherwise use Claude Sonnet High or Codex Terra High. Missing task context assumes non-Low conservatively and discloses that assumption. If the current selected pair matches, say the recommendation is met. Implicit loading, status, and off do not trigger the enabling suggestion. Mode changes preserve evidence and never disable native orchestration or cancel useful work. Disabling invalidates pending learning from that session generation, including pre-off work finishing after re-enable; newly prepared work can learn after re-enable.

A preparation contract alone is not an actual assignment or execution receipt. Discover supported requested controls and known precedence conflicts before launch; unsupported controls or a known mismatch remain capability blockers. Missing post-run provider receipts alone do not block an otherwise permitted dispatch. Report its actual assignment ID and requested model/effort as requested-only attribution. Only independently reviewed outputs with the actual exact model, effective effort, distinct execution ID, attributed run/epoch, and verified assessment can enter a performance window. Keep unknown, mismatched, cached, or opaque native-worker results out of learning and report the exclusion. The controller validates submitted attribution; it cannot independently authenticate a user, observe a provider runtime, or establish output quality.

## Deterministic decision

1. Identify the current track and its initial floor. Discover available model/effort pairs without changing session settings.
2. If the current rung is unavailable, select the nearest supported higher rung, start a fresh epoch, and report a capability fallback. If none exists, report the blocker. Never lower a floor to bypass access limits.
3. Filter assessments to the exact track and current epoch. Exclude unverified or unattributed results. Sort by assessment timestamp in UTC; use original CSV append order for ties, and take the newest five.
4. With fewer than five, retain the current rung. With five and average ≤4.5, move to the nearest available higher rung. With five perfect scores, move to the nearest available lower rung at or above the floor. Otherwise retain the rung. At a bound, retain it and report the bound.
5. Start a fresh epoch on a rung change, a changed exact model version, a capability fallback, a changed role-policy lineage, or explicitly unrecoverable attribution. A context change that retains the rung preserves the epoch and window. If a full window retains the current rung, the next eligible assessment rolls that window forward. Other tracks never affect it.

With five integer scores, the largest average triggering promotion is 4.4; 4.6 and 4.8 retain the rung, and 5.0 triggers a downward move when permitted. There is no attainable 4.5 average in a five-integer window. The policy retains the source threshold exactly.

Availability changes apply prospectively. They must not rewrite past transitions. Recheck skipped rungs on a new session or after a known capability change; do not silently descend into a newly available rung without the required performance evidence or explicit user policy revision. A model-version change invalidates that version's old performance window, even at the same logical rung.

## Reporting and bounds

Before launch, identify the actual role/model/effort and its selection basis. After independent assessment, give a concise result, verified evidence, material deficits, unverified items, rework status, and ladder decision, following any required project micro-report format. Keep verbose arithmetic out of ordinary progress updates unless required or requested. The source's silence rule cannot suppress required reporting.

After two unsuccessful repair cycles for one issue, stop repeating the approach and diagnose inputs, decomposition, assumptions, or verification. There is no automatic permission to skip five-run evidence because one result failed. Consult the current Advisor when complexity or Orchestrator difficulty requires it. At the ladder ceiling, change the approach and report unresolved limitations; never lower acceptance criteria or create endless advisory/rework chains.
