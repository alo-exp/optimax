# Optimax 0.1.0 verification

Checked 2026-11-07. This initial release has a verified shared controller and distributed artifacts, with the host and publication limits below. It is not a claim of universal native integration or measured cost savings.

| Area | Observed evidence | Status |
| --- | --- | --- |
| Shared Python runtime and release builder | 125 tests passed; historical policy IDs and event lineage preserved | Passed |
| Website behavior | Eight Node tests including real DOM search/keyboard coverage; static build generates 16 articles and 36 indexed sections | Passed |
| Portable plugin manifest | Published Agent Plugins JSON schema validation passed | Passed |
| Standalone skill | Official skill validator passed on fresh extraction | Passed |
| Release contents | 14 standalone and 17 plugin files match canonical source; no personal ledger, tests, caches or session reports | Passed |
| Installed controller | Fresh install, no-overwrite, disabled status, explicit/idempotent on, off, recovery, malformed native context and disabled preparation checks | Passed in disposable fixtures |
| Codex direct helper path | Actual Advisor/Executor collaboration calls used the controller before and after rename; an actual Codex helper independently checked the extracted artifacts | Passed for explicitly loaded skill; not registered-plugin discovery |
| Codex native plugin registry and CLI frontend | Marketplace registration cannot write host config; CLI frontend cannot initialize its in-process app-server in this restricted session | Blocked; not claimed verified |
| Claude package | JSON manifests, layout, component paths, namespace and shared Claude ladder/controller cases checked independently | Static checks passed |
| Claude live execution / Ultracode | Not invoked before the authorized quota-reset window | Deferred to Tuesday 10 November 2026, 14:00 Australia/Sydney |
| Website rendering and live interaction | Built-in browser unavailable: Mac locked and browser use disabled | Unverified |
| Public website access | Native public-access mutation rejected by the session approval policy | Blocked |
| Custom domain | optimax.alolabs.dev had no DNS record at inspection; Cloudflare is authoritative; no DNS credential available in this session | Pending configuration |
| Tuesday automation | Scheduling tool rejected creation because approval policy is never | Not scheduled; runbook prepared |

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
