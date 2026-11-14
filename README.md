# Optimax

Optimax is a portable skill and thin plugin for choosing delegated Executor and Advisor models using independently assessed results. It keeps your selected orchestrator in charge and stores learning per user and project. Created by Shafqat Ullah at Ālo Labs. Source: [alo-exp/optimax](https://github.com/alo-exp/optimax); [website on GitHub Pages](https://alo-exp.github.io/optimax/). The custom hostname `optimax.alolabs.dev` awaits a separate DNS cutover.

## Install

This checkout prepares Optimax v0.2.0 as an unpublished prerelease candidate; see the [candidate release notes](CHANGELOG.md). The catalog commands below resolve the published catalog, whose update to this candidate remains pending. Install through the unified Ālo Labs [agent-plugins catalog](https://github.com/alo-labs/agent-plugins), with host-specific catalog entries. These commands require marketplace support in your client. This source checkout bundles two skills in `optimax-plugin.zip`: the model-selection policy at `skills/optimax/` and the staged review workflow at `skills/review-ladder/`. The added review skill has not yet been qualified through published catalog installation or live host discovery. Avoid loading a second standalone copy of Optimax alongside the plugin.

For Codex, register the catalog, install, and list installed plugins:

```sh
codex plugin marketplace add alo-labs/agent-plugins
codex plugin add optimax@alo-labs-codex
codex plugin list --json
```

In Claude Code, use:

```text
/plugin marketplace add alo-labs/agent-plugins
/plugin install optimax@alo-labs
```

The Claude commands have been checked against documentation; live Claude acceptance is deferred. The v0.1.0 Codex plugin passed native installation, installed-skill discovery and session control checks on CLI 0.166.0-alpha.6; see the [historical native acceptance record](docs/CODEX-ACCEPTANCE.md) and the [current verification report](docs/VERIFICATION.md) for candidate coverage and separate historical v0.1.1 evidence.

## Run a review ladder

Use [Review Ladder](skills/review-ladder/SKILL.md) for staged independent review, repair, and verification of a bounded scope. Once the host discovers the bundled skill, invoke `$review-ladder` in Codex or `/optimax:review-ladder` in Claude Code and supply the review scope. Short aliases depend on the host; use the discovered command name. Review Ladder follows its explicit, user-authorized model and effort sequence through the contracted rungs independently of whether Optimax's adaptive policy is on or off, subject to the host's model, effort, and delegation capabilities. Invoking it does not enable the adaptive policy or change the selected Orchestrator. The adaptive controller cannot represent every fixed review rung and has no fixed-rung override. A review with policy enabled and a valid matching pre-dispatch adaptive reservation follows ordinary adaptive eligibility rules. An unmatched fixed review, or one run when the policy is off, uses supported host dispatch and an ordinary durable review report with actual assignment IDs, requested settings, candidate/scope/pass and outcomes; these report-only reviews are excluded from adaptive learning even with a later receipt, and existing adaptive history is preserved. Unsupported fixed rungs block without substitution. Missing effective receipts remain explicit unknowns. Controller `launch` rows are reservations, and host confirmation, failure and cancellation are reported separately; see [the limited recording path](skills/optimax/references/calculator.md#fixed-review-and-dispatch-limits).

## Control a session

In Claude Code use `/optimax:optimax on`, `/optimax:optimax off`, or `/optimax:optimax status` to control or inspect the session. In Codex, invoke `$optimax` and supply the same options. Native Codex installation, discovery and session controls passed for v0.1.0 on the tested client; Claude live acceptance is deferred. Installation alone does not enable the policy.

Each explicit activation, including repeated `on`, checks conventional host instruction candidates for potential conflicts. The host must review their applicability and priority; the audit cannot prove which files loaded or that all instructions are compatible. See [instruction audit usage and limits](skills/optimax/references/calculator.md#instruction-audit-on-activation). Status and off do not run the audit.

The controller uses `PROJECTROOT/model-perf/<actual-user-id>-model-perf.csv`, where the project root is the canonical primary checkout and the user ID is a stable, verified identity. The rename does not reset or migrate learning: the historical `optimal-ultra-ladder-v1`, `v2`, and `v3` identifiers, lineage, events, and epochs remain intact. Keep project ledgers private.

Version 0.1.1 adds Windows-compatible controller locking and filesystem handling. Windows controllers sharing a project must use the same resolved user profile with a writable `~/.optimax/locks` cache; the shared profile location keeps lock coordination independent of temporary-directory settings. Permanent lock errors fail promptly. Portable regression tests cover these paths on POSIX; native Windows execution remains untested.

## Limits and verification

Optimax provides instructions and a deterministic controller; it cannot guarantee model availability, force a host to follow instructions, verify hidden native workers, or change the user's orchestrator. Native orchestration is only partially optimizable when worker model, effort, or attribution is opaque. Independent review remains the orchestrator's responsibility. See the [skill](skills/optimax/SKILL.md) and its references for policy, safety, and recovery.

Run `python3 -m unittest discover -s tests` for the local suite. Build the allowlisted, deterministic plugin archive with `python3 build_release.py --output dist`. If that directory contains the older `optimax-skill.zip`, the builder rejects it; choose a fresh output directory instead. Use a trusted output directory under exclusive control during the build: a concurrent uncooperative replacement may be overwritten, and a normal rebuild intentionally replaces the archive. The archive excludes project ledgers, caches, tests, and session reports. Live host discovery, control behavior, and published catalog resolution are separate acceptance gates.

The [verification report](docs/VERIFICATION.md) records checked revisions, artifact digests, the scope of native Codex and website qualification, and remaining coverage. Live Claude acceptance remains unverified; see the [acceptance runbook](docs/CLAUDE-ACCEPTANCE.md) for the authorized execution window and historical scheduling note.

The website source is in [site/](site/) and its design system is documented in [site/DESIGN-SYSTEM.md](site/DESIGN-SYSTEM.md). From `site/`, run `npm ci`, `npm test`, and `npm run build` to install the locked dependencies, test, and build the site.

MIT licensed; see [LICENSE](LICENSE).
