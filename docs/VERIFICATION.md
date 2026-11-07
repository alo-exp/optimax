# Optimax 0.1.0 verification

Website update checked 2026-11-08 Australia/Sydney. The purple light/dark and CMF messaging update passed 61 Node tests, static build, GitHub Pages deployment and live file verification. Original plugin v0.1.0 evidence is retained for the unchanged runtime. Browser-rendered acceptance remains explicitly unverified; no universal native integration or measured cost savings are claimed.

| Area | Observed evidence | Status |
| --- | --- | --- |
| Shared Python runtime and release builder | 125 tests passed; historical policy IDs and event lineage preserved | Passed |
| Website behavior | 61 Node tests covering theme preference/error/cross-tab state, actual palette contrast and gradients, generated theme controls, CMF/parallel positioning, existing keyboard/clipboard/search/path and workflow contracts; 17 articles and 40 indexed sections | Passed locally and in Actions; zero failures/skips |
| Portable plugin manifest | Published Agent Plugins JSON schema validation passed | Passed |
| Standalone skill | Official skill validator passed on fresh extraction | Passed |
| Release contents | 14 standalone and 17 plugin files match canonical source; no personal ledger, tests, caches or session reports | Passed |
| Installed controller | Fresh install, no-overwrite, disabled status, explicit/idempotent on, off, recovery, malformed native context and disabled preparation checks | Passed in disposable fixtures |
| Codex direct helper path | Real prepared Advisor/Executor calls used the controller before and after rename; native runtime banners independently establish exact model/effort | Passed for observed direct executions |
| Codex native plugin registry and CLI frontend | Global v0.1.0 installed/enabled from the pinned unified catalog; actual CLI 0.166.0-alpha.6 discovered its installed skill and passed on/off, idempotence and same-ID process recovery | Passed on tested client; unrelated settings preserved |
| Claude package | JSON manifests, layout, component paths, namespace and shared Claude ladder/controller cases checked independently | Static checks passed |
| Claude live execution / Ultracode | Not invoked before the authorized quota-reset window | Deferred to Tuesday 10 November 2026, 14:00 Australia/Sydney |
| Website rendering and live interaction | Built-in browser unavailable: Mac locked and browser use disabled | Unverified |
| Public website access | Purple/theme/CMF site deployed at https://alo-exp.github.io/optimax/; all 29 generated pages/assets returned HTTP 200 and matched the accepted build byte for byte. A nested unknown URL returned the custom HTTP 404 with current theme assets/control | Passed |
| Custom domain | optimax.alolabs.dev awaits a separate GitHub Pages cutover; eventual CNAME is alo-exp.github.io. Earlier Sites validation records are obsolete for this target; no DNS changes made | Pending; not live yet |
| Tuesday automation | Active one-occurrence heartbeat saved for Tuesday 10 November 2026 at 14:00 on the verified Australia/Sydney host timezone (03:00 UTC) | Scheduled; not executed yet |
| Fresh Codex session | A second real native Terra Low session discovered the plugin and returned disabled status under its distinct actual thread ID; fixture ledger hash unchanged | Passed; not a compaction test |

Publication evidence: signed plugin commit [`54540db`](https://github.com/alo-exp/optimax/commit/54540db3ea74374677438995d9fce83b58e1441d), signed tag and [v0.1.0 preview release](https://github.com/alo-exp/optimax/releases/tag/v0.1.0); signed marketplace commit [`bd142cc`](https://github.com/alo-labs/agent-plugins/commit/bd142ccb3ecb5c0bb0572aedc5be76666a97c842). Both catalogs pin the tested plugin SHA, and release digests match the table below. The website was migrated from the earlier Sites preview to GitHub Pages from signed commit [`de88199`](https://github.com/alo-exp/optimax/commit/de88199e617c0d3fb4a4fa97f41f7b98a95b08ba); [Actions run 42373055544](https://github.com/alo-exp/optimax/actions/runs/42373055544) passed build and deployment. Its upstream actions emitted Node 20 deprecation and Ubuntu image-migration notices while completing successfully. Browser rendering remains unverified; HTTP and DOM checks do not substitute for it.

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

See the [native Codex acceptance record](CODEX-ACCEPTANCE.md) and [deferred Claude runbook](CLAUDE-ACCEPTANCE.md). The Claude automation is scheduled but has not executed. Update qualification claims only from observed host evidence.

## GitHub Pages migration evidence

- `node --test tests/pages-paths.test.js` from `site/`: six initial tests failed before production changes on missing deployment-prefix/configuration behavior, then passed after implementation. The primary agent independently reran those regressions against archived `f6d2701` and confirmed six expected failures.
- `node --test --test-name-pattern='complete generated graph' tests/pages-paths.test.js`: a subsequent robots-boundary assertion failed for both prefixed variants before the Allow path repair, then passed. Seven deployment tests now cover the default project URL, the configure-pages URL without a trailing slash, root-domain mode, every generated local target/anchor, invalid configuration before cleanup, and built-client fetch/result/Enter/error behavior.
- `node --test tests/pages-workflow.test.js`: failed with the expected missing-workflow assertion before the workflow was created, then passed. Independent review checked the official pinned action contracts. Additional characterization assertions were added from a passing baseline for existing correct credential, action-identity and success-gating behavior; no artificial red phase is claimed for those assertions.
- `npm test` and `npm run build`: 17 tests passed and the static build succeeded. Generated-artifact review found 27 intended public files, no symlinks and no source, credential, configuration or learning directories.
- GitHub Actions completed the same tests, build, upload and deployment successfully. HTTPS checks verified all 27 generated files byte for byte at the project URL, plus the custom nested-route 404. Browser access remains disabled and the Mac locked. Custom-domain DNS was not changed.

## Purple themes and CMF messaging update

The supplied Content Messaging Framework v3.0 informed the product-page definition, compact audience/problem/future sequence, mechanism, inspectable proof, benefits, objections before installation, and first-session guidance. [MESSAGING.md](../site/MESSAGING.md) records the adaptation and evidence boundaries. No conversion statistics, testimonials, scarcity or outcomes were invented. Useful parallelization is presented alongside model routing, with verified-capacity, dependency and ownership limits.

Observed TDD and regression evidence (commands from `site/`):

- `node --test tests/theme.test.js`: 26 initial behavioral failures against an empty seam, then 26 passes. Three additional characterization cases established later-body binding, next-page restore and early cross-tab synchronization. `node --test --test-name-pattern='clear' tests/theme.test.js` then reproduced a cross-tab clear-all defect before its repair; final theme suite has 31 passes.
- `node --test tests/theme-contrast.test.js`: eight expected failures before the palette change, then eight passes. A subsequent hovered-link regression reproduced 2.32:1 contrast on a technical surface before its scoped accent repair; nine cases now check actual tokens, sampled gradients, reading/focus pairs, preference fallback and control contracts.
- `node --test tests/site-contract.test.js`: four expected assertion failures before shared markup/copy changes, then four passes. Existing install commands and navigation contracts were preserved. All 20 generated HTML pages omit the personal footer credit and include the early classic theme script and accessible shared control.
- `rtk test npm test` and `npm run build`: full local suite and build passed after the combined source was stable. Artifact review found 29 allowlisted public files, no symlinks, no personal credit, and 17 articles / 40 search sections.
- Independent content/source review found no material gaps and checked 282 local URL occurrences. Actual browser rendering, pointer/keyboard interaction and visual responsive acceptance remain unverified because built-in browser use is disabled and the Mac locked. Source-level CSS contracts and DOM tests are not presented as a rendered audit.
- Publication: signed source commit [`d579153`](https://github.com/alo-exp/optimax/commit/d5791538f672a3e9858a349ff52eef268b4b2826) and [Actions run 42375920332](https://github.com/alo-exp/optimax/actions/runs/42375920332). CI reported 61 tests, 61 passes, zero failures and zero skips; build and deployment succeeded. Live checks verified all 29 files byte for byte, the new heading, removed credit, early theme script, parallel positioning and custom HTTP 404. No DNS changes were needed or made.
