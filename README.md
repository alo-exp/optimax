# Optimax

Optimax is a portable skill and thin plugin for choosing delegated Executor and Advisor models using independently assessed results. It keeps your selected orchestrator in charge and stores learning per user and project. Created by Shafqat Ullah at Ālo Labs. Source: [alo-exp/optimax](https://github.com/alo-exp/optimax); website: [optimax.alolabs.dev](https://optimax.alolabs.dev).

## Install

The intended distribution is the unified Ālo Labs [agent-plugins catalog](https://github.com/alo-labs/agent-plugins), with host-specific catalog entries. Publication is pending; these commands require the catalog entry to be published and supported by your client. The plugin contains the canonical skill at `skills/optimax/`; avoid loading a second standalone copy alongside it.

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

The Claude commands have been checked against documentation; live Claude acceptance is deferred. Codex plugin discovery and invocation remain unverified: the current host denied the configuration write required to register the catalog.

For a standalone Codex skill, obtain a source checkout and the release's `optimax-skill.zip`, then run from the checkout root:

```sh
python3 skills/optimax/scripts/install_local.py --archive /path/to/optimax-skill.zip
```

The destination defaults to `~/.codex/skills/optimax` and must not exist; use `--dest` to choose another existing-parent destination. The installer checks the archive before creating the destination and does not replace an existing directory.

## Control a session

In Claude Code use `/optimax:optimax on`, `/optimax:optimax off`, or `/optimax:optimax status` to control or inspect the session. In Codex, invoke `$optimax` and supply the same options. These instructions are interpreted by the host; Codex plugin discovery and invocation still require live acceptance, and Claude live acceptance is deferred. Installation alone does not enable the policy.

The controller uses `PROJECTROOT/model-perf/<actual-user-id>-model-perf.csv`, where the project root is the canonical primary checkout and the user ID is a stable, verified identity. The rename does not reset or migrate learning: the historical `optimal-ultra-ladder-v1`, `v2`, and `v3` identifiers, lineage, events, and epochs remain intact. Keep project ledgers private.

## Limits and verification

Optimax provides instructions and a deterministic controller; it cannot guarantee model availability, force a host to follow instructions, verify hidden native workers, or change the user's orchestrator. Native orchestration is only partially optimizable when worker model, effort, or attribution is opaque. Independent review remains the orchestrator's responsibility. See the [skill](skills/optimax/SKILL.md) and its references for policy, safety, and recovery.

Run `python3 -m unittest discover -s tests` for the local suite. Build allowlisted, deterministic skill and plugin archives with `python3 build_release.py --output dist`. The archives exclude project ledgers, caches, tests, and session reports. Live host discovery, control behavior, and published catalog resolution are separate acceptance gates.

The current [verification report](docs/VERIFICATION.md) separates passing core/artifact checks from blocked native installation, browser and public-access gates. Claude model execution is deferred until Tuesday 10 November 2026 at 14:00 Australia/Sydney; the [acceptance runbook](docs/CLAUDE-ACCEPTANCE.md) is prepared, but the restricted session could not queue an automation.

The website source is in [site/](site/) and its design system is documented in [site/DESIGN-SYSTEM.md](site/DESIGN-SYSTEM.md). From `site/`, run `npm ci`, `npm test`, and `npm run build` to install the locked dependencies, test, and build the site.

MIT licensed; see [LICENSE](LICENSE).
