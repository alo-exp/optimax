# Optimax verification

## 0.1.1 prerelease qualification — 9 November 2026

This release includes [Windows support PR #1](https://github.com/alo-exp/optimax/pull/1) and its follow-up corrections: a stable per-project lock in the resolved user profile, contention-only retries, and propagation of permanent lock failures. Controllers must share the same resolved profile with a writable local `~/.optimax/locks` cache; network filesystems remain unsupported.

| Area | Observed evidence | Scope |
| --- | --- | --- |
| Python runtime and release builder | 133 tests passed on macOS with Python 3.15.0 | Includes seven portable Windows-lock regressions; native Windows was not available |
| Release metadata | All three emitted plugin manifests identify 0.1.1 and match canonical source bytes | Checked against the current changelog release |
| Archive integrity and contents | Both ZIPs pass CRC checks; 14 skill files and 17 plugin files match canonical source | Deterministic allowlist excludes private ledgers, caches and tests |
| Fresh standalone installation | Emitted skill installs into a disposable directory, installed bytes match the archive, and controller status exits successfully with `enabled: false` | Package installation and controller smoke; not a new native Codex frontend qualification |
| Windows locking | Portable regressions cover real process exclusion across different temporary environments, permanent errors, contention, retained cache locks, unavailable-cache failure and cleanup | Uses a real POSIX lock adapter; native `msvcrt`, Windows ACL and rename behavior remain untested |
| Native host acceptance | The recorded Codex frontend evidence below remains specific to v0.1.0; Claude live acceptance remains deferred to Tuesday 10 November 2026, 14:00 Australia/Sydney | No new native frontend acceptance is claimed for this release |

The packaging integration regression was added before the version changes. The focused command `python3 -B -m unittest discover -s tests -p test_optimax_packaging.py -k test_release_archives_match_current_changelog_and_runtime_sources -v` first failed with three expected emitted-manifest version mismatches (`0.1.0` versus `0.1.1`), then passed after the manifest bump. The primary agent independently observed both phases and ran `python3 -B -m unittest discover -s tests`: 133 passed. Commands ran through RTK with bytecode writing disabled. The existing duplicate-ZIP fixture emits an expected warning while testing malformed archives.

| 0.1.1 artifact | Bytes | SHA-256 |
| --- | --- | --- |
| optimax-skill.zip | 50,686 | 44a208e8f18e6adfc479b68a89002467455d9303a2124cf76721837169f14412 |
| optimax-plugin.zip | 51,853 | 7b0ea27b07a823829fed1a341604f26cc38c93de9e6155bc0f21c94c3b85c4d5 |

The [v0.1.1 release](https://github.com/alo-exp/optimax/releases/tag/v0.1.1) identifies the delivered tag and assets. Both host catalogs in [alo-labs/agent-plugins](https://github.com/alo-labs/agent-plugins) must pin that tag and its exact commit; catalog publication and installed-host updates are separate checks. Website source is unchanged by the 0.1.1 packaging update, so its dated acceptance records below remain historical.

## Historical 0.1.0 verification

Website qualification updated 2026-11-08 Australia/Sydney. The selected Circuit production homepage and CMF copy passed 123 Node tests, the static build and 138 isolated Chromium cases across root-domain and GitHub project-prefix builds. Original plugin v0.1.0 evidence is retained for the unchanged runtime. Local rendered acceptance, CI publication and post-deployment HTTP verification are distinct gates; no universal native integration or measured savings are claimed.

| Area | Observed evidence | Status |
| --- | --- | --- |
| Shared Python runtime and release builder | 125 tests passed; historical policy IDs and event lineage preserved | Passed |
| Website behavior | 123 Node cases covering production Circuit/CMF copy, both deployment paths, theme/error/cross-tab behavior, keyboard/clipboard/search, historical previews and preserved Help; 17 articles and 40 indexed sections | Passed locally; publication CI reruns the checks |
| Portable plugin manifest | Published Agent Plugins JSON schema validation passed | Passed |
| Standalone skill | Official skill validator passed on fresh extraction | Passed |
| Release contents | 14 standalone and 17 plugin files match canonical source; no personal ledger, tests, caches or session reports | Passed |
| Installed controller | Fresh install, no-overwrite, disabled status, explicit/idempotent on, off, recovery, malformed native context and disabled preparation checks | Passed in disposable fixtures |
| Codex direct helper path | Real prepared Advisor/Executor calls used the controller before and after rename; native runtime banners independently establish exact model/effort | Passed for observed direct executions |
| Codex native plugin registry and CLI frontend | Global v0.1.0 installed/enabled from the pinned unified catalog; actual CLI 0.166.0-alpha.6 discovered its installed skill and passed on/off, idempotence and same-ID process recovery | Passed on tested client; unrelated settings preserved |
| Claude package | JSON manifests, layout, component paths, namespace and shared Claude ladder/controller cases checked independently | Static checks passed |
| Claude live execution / Ultracode | Not invoked before the authorized quota-reset window | Deferred to Tuesday 10 November 2026, 14:00 Australia/Sydney |
| Website rendering and interaction | 138 local isolated Chromium cases at both deployment bases, including Sora/Help Mona fonts, saved themes, clipboard, FAQs, text/connector clearance, full first-viewport install actions and focus contrast | Passed locally; built-in browser remains disabled and Mac locked |
| Public website access | Last recorded completed publication before Circuit promotion: commit 36f5533, Actions run 42397684799, all 55 generated files returned HTTP 200 and matched the qualified build byte for byte | Historical publication passed; check the current workflow and post-deployment result for newer revisions |
| Custom domain | optimax.alolabs.dev awaits a separate GitHub Pages cutover; eventual CNAME is alo-exp.github.io. Earlier Sites validation records are obsolete for this target; no DNS changes made | Pending; not live yet |
| Tuesday automation | Active one-occurrence heartbeat saved for Tuesday 10 November 2026 at 14:00 on the verified Australia/Sydney host timezone (03:00 UTC) | Scheduled; not executed yet |
| Fresh Codex session | A second real native Terra Low session discovered the plugin and returned disabled status under its distinct actual thread ID; fixture ledger hash unchanged | Passed; not a compaction test |

Publication evidence: signed plugin commit [`54540db`](https://github.com/alo-exp/optimax/commit/54540db3ea74374677438995d9fce83b58e1441d), signed tag and [v0.1.0 preview release](https://github.com/alo-exp/optimax/releases/tag/v0.1.0); signed marketplace commit [`bd142cc`](https://github.com/alo-labs/agent-plugins/commit/bd142ccb3ecb5c0bb0572aedc5be76666a97c842). Both catalogs pin the tested plugin SHA, and release digests match the table below. The website was migrated from the earlier Sites preview to GitHub Pages from signed commit [`de88199`](https://github.com/alo-exp/optimax/commit/de88199e617c0d3fb4a4fa97f41f7b98a95b08ba); [Actions run 42373055544](https://github.com/alo-exp/optimax/actions/runs/42373055544) passed build and deployment. Its upstream actions emitted Node 20 deprecation and Ubuntu image-migration notices while completing successfully. Browser rendering was unverified at that migration; the current Circuit qualification below adds rendered acceptance. [Current website workflow runs](https://github.com/alo-exp/optimax/actions/workflows/pages.yml) identify the tested revision and deployment status.

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

## Historical GitHub Pages migration evidence

- `node --test tests/pages-paths.test.js` from `site/`: six initial tests failed before production changes on missing deployment-prefix/configuration behavior, then passed after implementation. The primary agent independently reran those regressions against archived `f6d2701` and confirmed six expected failures.
- `node --test --test-name-pattern='complete generated graph' tests/pages-paths.test.js`: a subsequent robots-boundary assertion failed for both prefixed variants before the Allow path repair, then passed. Seven deployment tests now cover the default project URL, the configure-pages URL without a trailing slash, root-domain mode, every generated local target/anchor, invalid configuration before cleanup, and built-client fetch/result/Enter/error behavior.
- `node --test tests/pages-workflow.test.js`: failed with the expected missing-workflow assertion before the workflow was created, then passed. Independent review checked the official pinned action contracts. Additional characterization assertions were added from a passing baseline for existing correct credential, action-identity and success-gating behavior; no artificial red phase is claimed for those assertions.
- `npm test` and `npm run build`: 17 tests passed and the static build succeeded. Generated-artifact review found 27 intended public files, no symlinks and no source, credential, configuration or learning directories.
- GitHub Actions completed the same tests, build, upload and deployment successfully. HTTPS checks verified all 27 generated files byte for byte at the project URL, plus the custom nested-route 404. Browser access remains disabled and the Mac locked. Custom-domain DNS was not changed.

## Historical purple themes and CMF messaging update

The supplied Content Messaging Framework v3.0 informed the product-page definition, compact audience/problem/future sequence, mechanism, inspectable proof, benefits, objections before installation, and first-session guidance. [MESSAGING.md](../site/MESSAGING.md) records the adaptation and evidence boundaries. No conversion statistics, testimonials, scarcity or outcomes were invented. Useful parallelization is presented alongside model routing, with verified-capacity, dependency and ownership limits.

Observed TDD and regression evidence (commands from `site/`):

- `node --test tests/theme.test.js`: 26 initial behavioral failures against an empty seam, then 26 passes. Three additional characterization cases established later-body binding, next-page restore and early cross-tab synchronization. `node --test --test-name-pattern='clear' tests/theme.test.js` then reproduced a cross-tab clear-all defect before its repair; final theme suite has 31 passes.
- `node --test tests/theme-contrast.test.js`: eight expected failures before the palette change, then eight passes. A subsequent hovered-link regression reproduced 2.32:1 contrast on a technical surface before its scoped accent repair; nine cases now check actual tokens, sampled gradients, reading/focus pairs, preference fallback and control contracts.
- `node --test tests/site-contract.test.js`: four expected assertion failures before shared markup/copy changes, then four passes. Existing install commands and navigation contracts were preserved. All 20 generated HTML pages omit the personal footer credit and include the early classic theme script and accessible shared control.
- `rtk test npm test` and `npm run build`: full local suite and build passed after the combined source was stable. Artifact review found 29 allowlisted public files, no symlinks, no personal credit, and 17 articles / 40 search sections.
- Independent content/source review found no material gaps and checked 282 local URL occurrences. Actual browser rendering, pointer/keyboard interaction and visual responsive acceptance remain unverified because built-in browser use is disabled and the Mac locked. Source-level CSS contracts and DOM tests are not presented as a rendered audit.
- Publication: signed source commit [`d579153`](https://github.com/alo-exp/optimax/commit/d5791538f672a3e9858a349ff52eef268b4b2826) and [Actions run 42375920332](https://github.com/alo-exp/optimax/actions/runs/42375920332). CI reported 61 tests, 61 passes, zero failures and zero skips; build and deployment succeeded. Live checks verified all 29 files byte for byte, the new heading, removed credit, early theme script, parallel positioning and custom HTTP 404. No DNS changes were needed or made.


## Circuit production homepage and complete CMF copy

The user selected the existing Circuit direction. A `gpt-6.1-sol` subagent at Max rewrote the supporting homepage narrative using the supplied CMF v3.0 guide. [MESSAGING.md](../site/MESSAGING.md) maps all 14 core components and eight companion sections, including justified compression and exclusions. The approved hero and subtitle remain exact. Seven FAQs, a direct definition, scoped evidence, free-plugin versus model-usage charges, off controls and a first-session next step replace the former supporting copy.

Observed qualification from `site/`:

- `rtk node --test tests/homepage-production.test.js`: both deployment fixtures first failed because the selected homepage stylesheet was absent; they passed after structural promotion. Before applying the revised copy, both failed on the expected old-title mismatch, then passed the complete accepted-copy contracts after integration.
- `rtk npm test`: 123 tests passed. Historical preview copy tests now use an attributable frozen body from commit 36f5533; their original assertions remain intact. The primary independently verified that fixture against the committed source.
- `rtk test npm run test:browser`: 138 cases passed across both deployment bases. Root coverage includes 320, 390, 768 and 1440 pixels in both themes, local fonts, fully visible installation controls, readable functional text, diagram clearance, all seven FAQ disclosures, actual clipboard behavior, theme persistence and focus contrast.
- Two classes of initial browser failures were test-model errors: reseeding storage on every reload and sampling the button fill instead of its offset focus outline. The corrected tests preserve explicit-choice persistence and the 3:1 focus-contrast requirement. These were test corrections, not production defect repairs.
- Build output has 57 files. All 54 previously published non-homepage files remain byte-for-byte unchanged; `index.html` changes and `assets/homepage.css` plus `assets/homepage-theme.js` are added. Existing Help, all four historical previews, source fonts and shared controls remain intact.
- Fourteen ignored local captures cover full pages, native desktop/mobile openings, proof, all expanded FAQ answers and installation. Rendered screenshots and public HTTP delivery checks have separate consumers; the former do not establish the latter.

Publication remains gated by the [website workflow](https://github.com/alo-exp/optimax/actions/workflows/pages.yml), followed by HTTP byte comparison against the qualified build. The dated plugin-host evidence above is unchanged; this website work does not establish Claude live acceptance, universal host support or measured time/cost savings.
