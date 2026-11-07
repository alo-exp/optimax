# Optimax 0.1.0 verification

Checked 2026-11-07. Plugin release v0.1.0 has a verified shared controller and distributed artifacts. The website's subsequent main-branch update has nine passing Node tests and a verified public deployment. Host and custom-domain limits remain explicit below; no universal native integration or measured cost savings are claimed.

| Area | Observed evidence | Status |
| --- | --- | --- |
| Shared Python runtime and release builder | 125 tests passed; historical policy IDs and event lineage preserved | Passed |
| Website behavior | Nine Node tests including real generated DOM, keyboard and exact multiline clipboard coverage; 16 articles and 36 indexed sections | Passed on website follow-up |
| Portable plugin manifest | Published Agent Plugins JSON schema validation passed | Passed |
| Standalone skill | Official skill validator passed on fresh extraction | Passed |
| Release contents | 14 standalone and 17 plugin files match canonical source; no personal ledger, tests, caches or session reports | Passed |
| Installed controller | Fresh install, no-overwrite, disabled status, explicit/idempotent on, off, recovery, malformed native context and disabled preparation checks | Passed in disposable fixtures |
| Codex direct helper path | Actual Advisor/Executor collaboration calls used the controller before and after rename; an actual Codex helper independently checked the extracted artifacts | Passed for explicitly loaded skill; not registered-plugin discovery |
| Codex native plugin registry and CLI frontend | Registration cannot write the host marketplace cache and the in-process app-server cannot initialize; both remain denied after the Full Access setting change | Blocked; not claimed verified |
| Claude package | JSON manifests, layout, component paths, namespace and shared Claude ladder/controller cases checked independently | Static checks passed |
| Claude live execution / Ultracode | Not invoked before the authorized quota-reset window | Deferred to Tuesday 10 November 2026, 14:00 Australia/Sydney |
| Website rendering and live interaction | Built-in browser unavailable: Mac locked and browser use disabled | Unverified |
| Public website access | Public deployment succeeded at https://optimax-alo-labs.tonedion1.chatgpt.site; all 26 built public routes/assets returned HTTP 200, including the 36-entry search index | Passed |
| Custom domain | optimax.alolabs.dev is attached to the host and awaits one CNAME plus two TXT records; Cloudflare's saved login is expired and the browser is unavailable | Pending DNS/SSL; not live yet |
| Tuesday automation | Scheduling tool rejected creation because approval policy is never | Not scheduled; runbook prepared |

Publication evidence: signed plugin commit [`54540db`](https://github.com/alo-exp/optimax/commit/54540db3ea74374677438995d9fce83b58e1441d), signed tag and [v0.1.0 preview release](https://github.com/alo-exp/optimax/releases/tag/v0.1.0); signed marketplace commit [`bd142cc`](https://github.com/alo-labs/agent-plugins/commit/bd142ccb3ecb5c0bb0572aedc5be76666a97c842). Both catalogs pin the tested source SHA. GitHub-reported asset digests match the table below. The live website was built from Sites source commit `cfde56ea43d98fa3e4b99245051f802881d74d66` and published as version 1. Browser rendering remains unverified; HTTP and DOM checks do not substitute for it.

## Reproduce source checks

```sh
python3 -m unittest discover -s tests -v
python3 build_release.py --output dist
cd site
npm ci
npm test
npm run build
```

The native plugin commands are documented in [INSTALL.md](../INSTALL.md). Run them in an authorized host session; passing the Python suite is not a replacement for actual plugin installation/discovery.

## Release archives

| Artifact | Bytes | SHA-256 |
| --- | --- | --- |
| optimax-skill.zip | 49,950 | 5ad8fb61608d9c5dd2fc3a121d7355dc17887d77501bf3812e997b60f901dfc9 |
| optimax-plugin.zip | 51,116 | ecabeda99861e3cb384b92ce5a706cf3d6602eac3ff9364085a395c0452342fa |

The builder uses deterministic ZIP metadata and an explicit runtime allowlist. It stages both archives before replacing existing outputs and rolls back caught promotion failures. Persistent rollback failure preserves recovery backups. Two separate archive renames are not a crash-atomic transaction; builds are serialized, and release hashes must be checked before upload.

## TDD and review

Observed red→green regressions covered the renamed archive contract, included license, organization metadata, staged release failures, promotion/rollback failures and search keyboard boundaries. Independent review found and prompted repair of stale invocation instructions, the archive overwrite failure and initial ArrowUp selection. The strengthened default-install-destination assertion and real-DOM integration expansion were added after their initial implementation; they are retrospective coverage, not a completed original TDD cycle for those particular assertions. No failures were hidden, tests skipped or thresholds weakened.

The private runtime ledger remains per project/user under model-perf/ and is excluded from the public repository and archives. A public rename did not rewrite optimal-ultra-ladder-v1/v2/v3 policy identities, epochs or existing event history. Tests that simulate quality scores or native context do not establish real helper execution or real Ultra/Ultracode access.

See [the deferred Claude runbook](CLAUDE-ACCEPTANCE.md). No scheduler was installed by that document. Update qualification claims only from observed host evidence.
