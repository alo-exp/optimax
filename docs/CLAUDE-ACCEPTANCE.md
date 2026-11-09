# Deferred Claude acceptance

Live Claude execution is authorized only from **Tuesday 10 November 2026, 14:00 Australia/Sydney** (03:00 UTC). Do not run Claude model work before this window. Static package inspection and shared controller tests are permitted now. The requested time is an execution window, not evidence that a job is currently scheduled or has run.

Historical scheduling note, dated 2026-11-07: the earlier acceptance record reported an active, one-occurrence native automation for that time, with the host timezone and one-run recurrence checked. This qualification has not reverified that saved configuration. Recheck the actual job configuration and report its state before relying on it; the host and credentials must be available. Neither the historical note nor a saved schedule establishes live Claude acceptance.

## Before model work

1. Verify the `alo-exp/optimax` release tag, matching source commit and release archive hashes. Check the `optimax` entry in both catalogs in `alo-labs/agent-plugins` resolves that tested revision.
2. Confirm current time and Claude quota. If quota is still unavailable, report the exact blocker; do not substitute a simulated receipt or claim live acceptance. Do not spend Anthropic API funds as a substitute for the authorized native session.
3. Use a disposable project and a test user identity for fixtures. Preserve the person's real project ledger, Orchestrator selection, native settings, existing plugin configuration and useful work.
4. Run the committed Python suite and website checks only if source/dependencies changed or prior evidence is no longer applicable. Use static Claude manifest and path checks to establish package integrity; they do not establish native execution.
5. Reconcile the accepted candidate, existing evidence, actual assignments and their host-returned IDs, useful running work, dependencies and verified free capacity. State remaining deliverables and execution owners before dispatch.
6. Inspect the installed client's actual Agent schema, model/effort controls and known precedence. Use local help and non-secret configuration first; consult current official host documentation if needed. Do not infer Claude host limitations from this package's lack of hooks.

## Automated qualification and limits

Qualification recorded on 2026-11-09 against source commit `7a1eaa977b3cf120c08471914e6782fa59a9efda` passed 61 existing tests: 19 in `test_native_dispatch.py`, 27 in `test_work_breakdown.py`, 6 in `test_session_policy.py`, and 9 focused `test_performance.py` cases covering mode state, strict receipt eligibility, duplicate execution, role/provider separation, late epochs and explicit-on recommendations. These are passing qualification checks on existing behavior, not a new red → green cycle or native Claude execution.

The adapter's missing-effective-evidence, known-conflicting-override and role-fence tests explicitly exercise both `claude-agent` and `codex-spawn`. The execution contract and readiness/history helper are shared and have no host-specific ownership branch. Most selected controller receipt/mode fixtures use Codex defaults; their passes qualify shared controller logic, not Claude host behavior. Two additional disposable Claude-parameterized controller qualification tests passed: on/status/off and generation exclusion; strict receipt learning and Advisor/Executor separation. These used only temporary fixture storage, with `direct` and `claude-ultracode` mode labels and synthetic fixture identities; they called no helper or provider and created no real assessment.

Static inspection confirmed that Claude uses the same `skills/optimax/SKILL.md` boundary and that this package contains no installed hooks. A supplied snapshot or `host_returned: true` remains a host claim; the helper does not authenticate an actual launch or intercept arbitrary tools.

**Native Claude direct Agent and Ultracode acceptance: NOT RUN in this qualification.** Native installation/discovery, actual Executor dispatch, effective model/effort receipts, useful native parallelism and delivered behavior remain to be observed in the authorized window. Preserve earlier evidence with its original date and scope; do not relabel it as evidence for a later candidate.

## Session controls

In Claude Code, verify these namespace commands against the installed client's supported interface:

```text
/plugin marketplace add alo-labs/agent-plugins
/plugin install optimax@alo-labs
/optimax:optimax status
/optimax:optimax on
/optimax:optimax on
/optimax:optimax off
/optimax:optimax status
```

Verify installation/discovery, the installed client's supported commands and actual namespace. Record responses and ledger effects. Status before enablement must not enable the policy or launch work; explicit and idempotent on must give an unapplied native-aware recommendation. Repeated on must not create another enablement generation. While enabled, `execution_contract` must report substantive ownership by an Executor, `advisor_authorizes_execution: false` and `automatic_root_fallback: false`. Status must preserve mode and remain read-only.

Off must stop policy dispatch, required consultation and learning while preserving native settings, the selected Orchestrator and useful in-flight work. Its contract must defer to `governing_host_policy` with `blanket_root_permission: false`; off does not waive other user/host rules or erase earlier authorization history. Reopen the same trusted session to verify durable recovery, and check that a different session remains off until explicitly enabled. Deliberately enable again before the enabled-session cases, then return the disposable session to off when finished.

## Fresh enabled-session execution

Use a small real task with an observable deliverable and meaningful TDD where behavior changes. Capture actual host conversation/tool events and resulting artifacts so an independent reviewer can distinguish each role and stage.

1. Obtain a separate, read-only Advisor consultation before finalizing the plan/design. Record its host-returned assignment ID and the root's independent decision. Advisors have no complexity tier, do not implement their recommendation in that advisory run, and cannot satisfy the Executor requirement. A leaf's local implementation reasoning must not start another policy scheduler. Do not let helpers score themselves.
2. Before substantive authoring, publish a visible checkpoint with remaining work, actual execution owner, dependencies, verified useful capacity, the host-returned Executor assignment ID, and either actual dispatch or a concrete blocker/permitted exception. A brief, controller reservation, prepared JSON or Advisor call alone is not dispatch. Refresh the checkpoint on material phase changes, resume/compaction, late correction and before acceptance.
3. Prepare a bounded Claude Executor on an actually available ladder pair, inspect the `claude-agent` adapter's checked arguments, then invoke the actual supported Agent tool. Retain the returned assignment ID, output and owned-file diff. Verify that implementation, test authoring, research, documentation, release preparation or semantic fixes were authored by that Executor. The root may inspect source, coordinate, run existing tests for independent verification, review and accept; those actions do not authorize root authoring.
4. Exercise useful parallelism with disjoint ready tasks when independently verified capacity exists. Record actual overlapping assignments, ownership and resource/dependency checks; do not count announced work or reservations as parallel dispatch. A dependent task starts after root acceptance. Unknown Ultracode occupancy is unknown, not zero; avoid competing direct fan-out without independently established disjoint capacity.
5. Before acceptance, reconcile every remaining substantive task with its actual Executor assignment or scoped permitted exception and independently inspect source, artifacts and test execution. Advisor output or a high assessment score does not close unassigned work. If the host fails to apply the boundary, report the deviation and leave live acceptance incomplete; a static helper pass is not enforcement evidence.

## Late correction and authorization history

Replay these declared-history cases through the checkpoint using disposable fixtures, then verify the host's correction behavior on any actual late correction. Fixture assignment IDs and receipts must never be reported as real native dispatch. Do not deliberately perform an unauthorized root edit to produce a deviation case.

| Declared situation | Required decision and evidence |
| --- | --- |
| Fresh enabled substantive work has only Advisor/planning evidence | Require actual Executor dispatch; root authoring remains disallowed. |
| Root work began with known unauthorized start | Preserve artifacts, `root_start_authorized: false` and `deviation: true`; delegate only remaining work. A new exception cannot erase the prior deviation. |
| Start authorization is unknown | Preserve `null` history. Current owner, off state or a new exception cannot establish prior authorization. |
| Root work began with known authorization | Preserve that history; it does not grant current permission for remaining enabled-session work. |
| An actual Executor or opaque native subtree already owns the stage | Continue or return to that owner and reconcile its actual host ID. Do not duplicate work to manufacture policy coverage. Accepted work has no remaining assignment. |
| Capacity, quota, capability, authentication, budget, host policy or dependencies block dispatch | Queue/replan and report the blocker. No automatic root fallback. Any exception for remaining root work needs applicable explicit authority and exact scope. |

A current exception governs only its supported scope and current permission. It does not rewrite prior authorization or override an already assigned execution owner. Record missing historical evidence instead of inventing retrospective assignments, authorizations or receipts.

## Requested controls, receipts and learning

Verify these separate boundaries for Claude:

- Supported requested model/effort controls permit otherwise authorized dispatch when effective receipt visibility is absent. Record the actual host assignment and requested-only settings; do not block merely for missing receipts and do not invent effective model, effort or execution ID.
- A known conflicting model or effort override must block the incompatible prepared route even without a verification flag. Missing supported requested controls require a compatible supported direct helper or a concrete capability blocker. Neither condition automatically permits root execution.
- Adapter provenance must retain `effective_settings_verified: false`. A caller's capability assertion, alias, completed call or matching fixture cannot authenticate effective settings. Establish real model/version, effort and execution ID from attributable runtime evidence.
- Only independently reviewed, genuinely executed and correctly attributed results enter learned model-specific windows. Requested-only, mismatched, unverified, duplicate/cached and off-generation results remain excluded. Never use synthetic identities to fill missing receipts or put quality-score fixtures in the person's actual learning ledger.
- With real receipts, check exact run/epoch/requested/effective consistency, independent review, serialized persistence and a later preparation restoring the state. Check duplicate execution exclusion, cached output reuse, off→on generation exclusion and late-epoch recovery in disposable fixtures. Receipt consistency does not establish provider authenticity or actual launch identity by itself.

## Claude Ultracode scope

Where actual Ultracode access exists, preserve existing native settings and use one actual execution owner per bounded stage. Record native state, actual dispatch route and supported stage controls separately. A `claude-ultracode` mode label does not activate that feature or prove a native launch. Preserve opaque native subtrees as single owned stages and leave hidden workers unscored.

Do not send flat model/effort/prompt fields to WorkflowInput; the package's `claude-workflow` adapter route is explicitly unsupported. Verify any real stage bridge's schema, return boundary and root acceptance independently. A supported direct `claude-agent` fallback qualifies only that direct controlled stage, not full Workflow integration. Missing requested controls block that route; missing only effective receipts permit requested-only dispatch with the learning limits above. Record partial coverage and exact blockers without claiming a host-wide hooks limitation.

## Report and repair

Record the exact source and installed revision/archive hashes, host/client version, current scheduling state, controls, native state, actual invocations/assignment IDs, ownership checkpoints, output/artifact observations, independent review, real effective-setting evidence and unverified cases. Separate observed automated/static qualification, real direct Agent results and real Ultracode results. Native cases remain NOT RUN or blocked until observed.

For every executable repair, write the smallest meaningful observable-behavior regression and record its expected behavioral failure before editing production code; implement, verify green, refactor with relevant tests passing and run required integration checks. Record exact red/green commands and outcomes. A new test that already passes is qualification/coverage, not a completed red phase. For behavior-preserving refactors, establish a passing characterization baseline; validate documentation-only changes without artificial failing tests.

Independently review the repaired candidate and run impacted checks before publishing. Update the public verification report, marketplace pin and website claims only with observed evidence for that candidate. Preserve historical evidence with its original date and scope. Successful direct Agent execution alone does not establish full Ultracode acceptance.
