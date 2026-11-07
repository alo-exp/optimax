# Deferred Claude acceptance

Live Claude execution is authorized only from **Tuesday 10 November 2026, 14:00 Australia/Sydney** (03:00 UTC). Do not run Claude model work before this window. Static package inspection and shared controller tests are permitted now.

A scheduling request was rejected by the current session's approval policy. **No automatic run is queued.** This runbook is preparation, not evidence that testing occurred or that a scheduler was installed.

## Before model work

1. Verify the `alo-exp/optimax` release tag, matching source commit and release archive hashes. Check the `optimax` entry in both catalogs in `alo-labs/agent-plugins` resolves that tested revision.
2. Confirm current time and Claude quota. If quota is still unavailable, report the exact blocker; do not substitute a simulated receipt or claim live acceptance.
3. Use a disposable project and a test user identity for fixtures. Preserve the person's real project ledger, Orchestrator selection, native settings, existing plugin configuration and useful work.
4. Run the committed Python suite and website checks only if source/dependencies changed or prior evidence is no longer applicable. Use static Claude manifest and path checks to establish package integrity; they do not establish native execution.

## Live cases

In Claude Code, use the currently supported commands:

```text
/plugin marketplace add alo-labs/agent-plugins
/plugin install optimax@alo-labs
/optimax:optimax status
/optimax:optimax on
/optimax:optimax on
/optimax:optimax off
/optimax:optimax status
```

Verify installation/discovery and the actual namespace. Status before enablement must not enable the policy; explicit and idempotent on must give an unapplied native-aware recommendation; off must stop policy dispatch, required consultation and learning while preserving native settings. Reopen a session to verify durable recovery under the correct session identity rather than claiming that every new session inherits enablement.

Perform one genuine bounded controlled helper assignment with a model and effort available on the verified ladder. Establish effective settings from attributable host evidence, independently review the output, and record only the real run. Advisors remain read-only and have no complexity tier. An Executor's local implementation reasoning does not start another policy scheduler. Do not let the helper score itself.

Where actual Ultracode access exists, verify one-owner-per-stage behavior, native setting preservation and root acceptance. Opaque internal workers remain unscored. Do not send flat model/effort/prompt fields to WorkflowInput; that adapter route is explicitly unsupported. If required controls or receipts are absent, record partial native coverage and the blocker.

Check duplicate execution exclusion, cached output reuse, off→on generation exclusion and recovery against disposable fixtures. Quality-score test fixtures are not real agent assessments and must never enter the person's actual learning ledger.

## Report and repair

Record the exact revision, host/client version, available controls, actual invocation, observations, real effective-setting evidence and unverified cases. Use mandatory TDD for executable repairs. Independently review the repaired candidate and run impacted checks before publishing changes. Update the public verification report, marketplace pin and website claims only with observed evidence. Keep Claude and Ultracode claims separate; a successful direct Agent call is not full Workflow integration.
