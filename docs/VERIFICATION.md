# Optimax verification

## 0.2.0 unpublished candidate — 9 November 2026

This source candidate adds Review Ladder, the Opus Max policy and audit corrections. It is not a published release. No v0.2.0 tag, download digest, catalog update or live installed-host result is established by the local checks below. Historical v0.1.1 artifact hashes and v0.1.0 native Codex acceptance remain separate evidence.

Activation-audit changes made after the recorded snapshots require their own qualification. The historical test snapshot's exact identity is unavailable in this record; the native forward evaluation identifies its own snapshot below. Neither establishes live audit behavior or complete host instruction discovery.

| Area | Observed candidate evidence | Scope |
| --- | --- | --- |
| Python suite | `python3 -B -m unittest discover -s tests`: 184 tests passed on macOS | Historical snapshot, exact identity unavailable; previous baseline was 183 tests and one candidate-version packaging regression was added. Coverage included the since-removed standalone installer. |
| Release metadata TDD | `python3 -m unittest discover -s tests -p test_optimax_packaging.py` first ran seven tests with four expected assertion failures: three emitted ZIP manifests identified 0.1.1 rather than 0.2.0, and the changelog lacked the candidate heading | Parent independently observed the red result before authorizing the version edits; historical snapshot identity unavailable |
| Packaging green | `python3 -B -m unittest discover -s tests -p test_optimax_packaging.py`: seven tests passed after the three manifest versions and changelog were updated | Historical snapshot identity unavailable; covered emitted archives, source-byte and changelog agreement, deterministic output, the since-removed standalone installer, and exclusion of private state. This does not establish current candidate coverage. |
| Review Ladder bundle | Earlier packaging regressions required all three runtime assets: `SKILL.md`, `agents/openai.yaml` and `references/report-template.md` | Historical snapshot contained both skills in the plugin and Optimax alone in a standalone archive; evidence for the current plugin-only candidate remains pending |
| Review sequence acceptance | Complete eight-rung qualification remains pending | A prior Terra Low review of an earlier candidate does not establish qualification of this release candidate or later changes |
| Native hosts and publication | New plugin-command discovery, published catalog resolution, Claude live acceptance and native Windows execution remain unverified | Instruction and portable regression coverage do not establish live host acceptance |

Commands ran through RTK. The historical full suite emitted the expected duplicate-ZIP warning from the malformed-archive fixture. Those local source tests covered the controller, policy contracts, review instructions and archive builder on that historical snapshot; static instruction checks do not prove a host executed the complete review ladder. No published artifact hashes are claimed for this candidate.

### Issue #2 ownership and native forward evaluation

The [issue #2](https://github.com/alo-exp/optimax/issues/2) candidate makes substantive Executor ownership explicit and adds readiness checkpoints around test, implementation and documentation work. Supported requested model and effort controls can permit dispatch without an effective-setting receipt; unknown effective settings must not produce learned scores. Recovery after work has already begun must identify the earlier unprepared work and apply the contract prospectively, without claiming retroactive compliance.

The [native forward evaluation record](CODEX-ACCEPTANCE.md#candidate-forward-evaluation-2026-11-09) identifies the evaluated snapshot and its limits. A fresh Codex CLI run read the copied candidate skill, dispatched an Advisor and a bounded Executor, and showed an Executor ownership checkpoint. The recorded root changes were controller-request and readiness metadata; the completed fixture contained the repair, regression tests and usage documentation. The root verified the test-only phase before authorizing production changes, and an independent evaluator reproduced the intended regression failures against the seeded implementation and observed the repaired fixture passing.

This is scoped evidence for that snapshot and task. It does not establish complete child patch traces, effective helper model/effort receipts, parallel Executor scheduling, adaptive cost routing, direct fallback, late correction, compaction recovery or universal enforcement against root actions. The disposable ledger learned no scores. A later checkpoint-history repair falls outside that native run. Final source qualification and the complete eight-rung review sweep remain pending; the candidate remains unpublished. Historical native runs below retain their original release scope, and no Claude or native Windows result is added here.

## 0.1.1 prerelease qualification — 9 November 2026

Optimax v0.1.1 included [Windows support PR #1](https://github.com/alo-exp/optimax/pull/1) and its follow-up corrections: a stable per-project lock in the resolved user profile, contention-only retries, and propagation of permanent lock failures. Controllers must share the same resolved profile with a writable local `~/.optimax/locks` cache; network filesystems remain unsupported.

| Area | Observed evidence | Scope |
| --- | --- | --- |
| Python runtime and release builder | 133 tests passed on macOS with Python 3.15.0 | Included seven portable Windows-lock regressions; native Windows was not available |
| Release metadata | All three emitted plugin manifests identified 0.1.1 and matched the qualified 0.1.1 source bytes | Checked against the changelog release at that qualification |
| Archive integrity and contents | Both ZIPs passed CRC checks; 14 skill files and 17 plugin files matched the qualified source | The deterministic allowlist excluded private ledgers, caches and tests |
| Fresh standalone installation | The emitted skill installed into a disposable directory, installed bytes matched the archive, and controller status exited successfully with `enabled: false` | Package installation and controller smoke; not a new native Codex frontend qualification |
| Windows locking | Portable regressions covered real process exclusion across different temporary environments, permanent errors, contention, retained cache locks, unavailable-cache failure and cleanup | Used a real POSIX lock adapter; native `msvcrt`, Windows ACL and rename behavior were not exercised by that qualification |
| Native host acceptance | The recorded Codex frontend evidence below remains specific to v0.1.0; the historical authorization specified an execution window starting Tuesday 10 November 2026, 14:00 Australia/Sydney | No new native frontend acceptance is claimed for this release |

The packaging integration regression was added before the version changes. The focused command `python3 -B -m unittest discover -s tests -p test_optimax_packaging.py -k test_release_archives_match_current_changelog_and_runtime_sources -v` first failed with three expected emitted-manifest version mismatches (`0.1.0` versus `0.1.1`), then passed after the manifest bump. The primary agent independently observed both phases and ran `python3 -B -m unittest discover -s tests`: 133 passed. Commands ran through RTK with bytecode writing disabled. The duplicate-ZIP fixture emitted the expected warning during those malformed-archive tests.

| 0.1.1 artifact | Bytes | SHA-256 |
| --- | --- | --- |
| optimax-skill.zip | 50,686 | 44a208e8f18e6adfc479b68a89002467455d9303a2124cf76721837169f14412 |
| optimax-plugin.zip | 51,853 | 7b0ea27b07a823829fed1a341604f26cc38c93de9e6155bc0f21c94c3b85c4d5 |

The [v0.1.1 release](https://github.com/alo-exp/optimax/releases/tag/v0.1.1) identifies the delivered tag and assets. That qualification required both host catalogs in [alo-labs/agent-plugins](https://github.com/alo-labs/agent-plugins) to pin that tag and its exact commit; catalog publication and installed-host updates are separate checks. Website source was unchanged by the 0.1.1 packaging update, so its dated acceptance records below remain historical.

## Historical 0.1.0 verification

Website qualification updated 2026-11-08 Australia/Sydney. The selected Circuit production homepage and CMF copy passed 123 Node tests, the static build and 138 isolated Chromium cases across root-domain and GitHub project-prefix builds. Original plugin v0.1.0 evidence is retained for that release's runtime. Local rendered acceptance, CI publication and post-deployment HTTP verification are distinct gates; no universal native integration or measured savings are claimed.

| Area | Observed evidence | Status |
| --- | --- | --- |
| Shared Python runtime and release builder | 125 tests passed; historical policy IDs and event lineage preserved | Passed |
| Website behavior | 123 Node cases covering production Circuit/CMF copy, both deployment paths, theme/error/cross-tab behavior, keyboard/clipboard/search, historical previews and preserved Help; 17 articles and 40 indexed sections | Passed locally at that qualification; local checks alone did not establish publication |
| Portable plugin manifest | Published Agent Plugins JSON schema validation passed | Passed |
| Standalone skill | Official skill validator passed on fresh extraction | Passed |
| Release contents | 14 standalone and 17 plugin files matched the qualified 0.1.0 source; the archives contained no personal ledger, tests, caches or session reports | Passed |
| Installed controller | Fresh install, no-overwrite, disabled status, explicit/idempotent on, off, recovery, malformed native context and disabled preparation checks | Passed in disposable fixtures |
| Codex direct helper path | Real prepared Advisor/Executor calls used the controller before and after rename; native runtime banners independently established the exact model and effort for those observed direct executions | Passed for observed direct executions |
| Codex native plugin registry and CLI frontend | Global v0.1.0 installed/enabled from the pinned unified catalog; actual CLI 0.166.0-alpha.6 discovered its installed skill and passed on/off, idempotence and same-ID process recovery | Passed on tested client; unrelated settings preserved |
| Claude package | JSON manifests, layout, component paths, namespace and shared Claude ladder/controller cases checked independently | Static checks passed |
| Claude live execution / Ultracode | Not invoked before the authorized quota-reset window in the historical record | That historical qualification did not establish live acceptance |
| Historical Circuit rendering and interaction | 138 local isolated Chromium cases at both deployment bases, including Sora/Help Mona fonts, saved themes, clipboard, FAQs, text/connector clearance, full first-viewport install actions and focus contrast | Passed locally; the built-in browser was disabled and the Mac locked during that qualification |
| Public website access | Last recorded completed publication before Circuit promotion: commit 36f5533, Actions run 42397684799, all 55 generated files returned HTTP 200 and matched the qualified build byte for byte | Historical publication passed; check the current workflow and post-deployment result for newer revisions |
| Custom domain | The historical record said optimax.alolabs.dev awaited a separate GitHub Pages cutover, with eventual CNAME alo-exp.github.io; no DNS changes were made during that work | Pending at that time; check current DNS and deployment separately |
| Tuesday automation | On 7 November 2026, the acceptance record reported an active one-occurrence heartbeat for 10 November at 14:00 Australia/Sydney (03:00 UTC) | Historical scheduling evidence only; that record established no later configuration revalidation or execution result |
| Fresh Codex session | A second real native Terra Low session discovered the plugin and returned disabled status under its distinct actual thread ID; fixture ledger hash unchanged | Passed; not a compaction test |

Publication evidence: signed plugin commit [`54540db`](https://github.com/alo-exp/optimax/commit/54540db3ea74374677438995d9fce83b58e1441d), signed tag and [v0.1.0 preview release](https://github.com/alo-exp/optimax/releases/tag/v0.1.0); signed marketplace commit [`bd142cc`](https://github.com/alo-labs/agent-plugins/commit/bd142ccb3ecb5c0bb0572aedc5be76666a97c842). At that publication, both catalogs pinned the tested plugin SHA, and release digests matched the historical table below. The website was migrated from the earlier Sites preview to GitHub Pages from signed commit [`de88199`](https://github.com/alo-exp/optimax/commit/de88199e617c0d3fb4a4fa97f41f7b98a95b08ba); [Actions run 42373055544](https://github.com/alo-exp/optimax/actions/runs/42373055544) passed build and deployment. Its upstream actions emitted Node 20 deprecation and Ubuntu image-migration notices while completing successfully. Browser rendering was unverified at that migration; the historical Circuit qualification below records later rendered acceptance for that earlier candidate. [Current website workflow runs](https://github.com/alo-exp/optimax/actions/workflows/pages.yml) identify the tested revision and deployment status.

## Reproduce source checks

```sh
python3 -m unittest discover -s tests -v
python3 build_release.py --output dist
cd site
npm ci
npm test
npm run build
```

Use a trusted output directory under exclusive control during the build. If `dist` contains the older `optimax-skill.zip`, the builder rejects it; pass a fresh output directory with `--output` instead. A normal rebuild intentionally replaces the plugin archive, and a concurrent uncooperative replacement may be overwritten.

The native plugin commands are documented in [INSTALL.md](../INSTALL.md). Run them in an authorized host session; passing the Python suite is not a replacement for actual plugin installation/discovery.

## Historical 0.1.0 release archives

| Artifact | Bytes | SHA-256 |
| --- | --- | --- |
| optimax-skill.zip | 49,950 | 5ad8fb61608d9c5dd2fc3a121d7355dc17887d77501bf3812e997b60f901dfc9 |
| optimax-plugin.zip | 51,116 | ecabeda99861e3cb384b92ce5a706cf3d6602eac3ff9364085a395c0452342fa |

For the historical two-archive builder, deterministic ZIP metadata and an explicit runtime allowlist were used. It staged both archives before replacing existing outputs and rolled back caught promotion failures. Persistent rollback failure preserved recovery backups. Two separate archive renames were not a crash-atomic transaction; builds were serialized, and release hashes required checking before upload. This record does not establish build evidence or complete qualification for the later plugin-only candidate.

## Historical TDD and review

The earlier qualification recorded red→green regressions covering the renamed archive contract, included license, organization metadata, staged release failures, promotion/rollback failures and search keyboard boundaries. Independent review found and prompted repair of stale invocation instructions, the archive overwrite failure and initial ArrowUp selection. The strengthened default-install-destination assertion and real-DOM integration expansion were added after their initial implementation; they are retrospective coverage, not a completed original TDD cycle for those particular assertions. No failures were hidden, tests skipped or thresholds weakened.

The private runtime ledger remains per project/user under model-perf/ and is excluded from the public repository and archives. A public rename did not rewrite optimal-ultra-ladder-v1/v2/v3 policy identities, epochs or existing event history. Tests that simulate quality scores or native context do not establish real helper execution or real Ultra/Ultracode access.

See the [native Codex acceptance record](CODEX-ACCEPTANCE.md) and [deferred Claude runbook](CLAUDE-ACCEPTANCE.md). Recheck the automation state before relying on it; update qualification claims only from observed host evidence.

## Historical GitHub Pages migration evidence

- `node --test tests/pages-paths.test.js` from `site/`: six initial tests failed before production changes on missing deployment-prefix/configuration behavior, then passed after implementation. The primary agent independently reran those regressions against archived `f6d2701` and confirmed six expected failures.
- `node --test --test-name-pattern='complete generated graph' tests/pages-paths.test.js`: a subsequent robots-boundary assertion failed for both prefixed variants before the Allow path repair, then passed. Seven deployment tests at that qualification covered the default project URL, the configure-pages URL without a trailing slash, root-domain mode, every generated local target/anchor, invalid configuration before cleanup, and built-client fetch/result/Enter/error behavior.
- `node --test tests/pages-workflow.test.js`: failed with the expected missing-workflow assertion before the workflow was created, then passed. Independent review checked the official pinned action contracts. Additional characterization assertions were added from a passing baseline for existing correct credential, action-identity and success-gating behavior; no artificial red phase is claimed for those assertions.
- `npm test` and `npm run build`: 17 tests passed and the static build succeeded. Generated-artifact review found 27 intended public files, no symlinks and no source, credential, configuration or learning directories.
- GitHub Actions completed the same tests, build, upload and deployment successfully. HTTPS checks verified all 27 generated files byte for byte at the project URL, plus the custom nested-route 404. Browser access was disabled and the Mac locked during that migration. Custom-domain DNS was not changed.

## Historical purple themes and CMF messaging update

The supplied Content Messaging Framework v3.0 informed the product-page definition, compact audience/problem/future sequence, mechanism, inspectable proof, benefits, objections before installation, and first-session guidance. [MESSAGING.md](../site/MESSAGING.md) records the adaptation and evidence boundaries. No conversion statistics, testimonials, scarcity or outcomes were invented. That update presented useful parallelization alongside model routing, with verified-capacity, dependency and ownership limits.

Observed TDD and regression evidence (commands from `site/`):

- `node --test tests/theme.test.js`: 26 initial behavioral failures against an empty seam, then 26 passes. Three additional characterization cases established later-body binding, next-page restore and early cross-tab synchronization. `node --test --test-name-pattern='clear' tests/theme.test.js` then reproduced a cross-tab clear-all defect before its repair; the final theme suite recorded 31 passes.
- `node --test tests/theme-contrast.test.js`: eight expected failures before the palette change, then eight passes. A subsequent hovered-link regression reproduced 2.32:1 contrast on a technical surface before its scoped accent repair; nine cases at that qualification checked actual tokens, sampled gradients, reading/focus pairs, preference fallback and control contracts.
- `node --test tests/site-contract.test.js`: four expected assertion failures before shared markup/copy changes, then four passes. Existing install commands and navigation contracts were preserved. All 20 generated HTML pages in that build omitted the personal footer credit and included the early classic theme script and accessible shared control.
- `rtk test npm test` and `npm run build`: full local suite and build passed after the combined source was stable. Artifact review found 29 allowlisted public files, no symlinks, no personal credit, and 17 articles / 40 search sections.
- Independent content/source review found no material gaps and checked 282 local URL occurrences. Actual browser rendering, pointer/keyboard interaction and visual responsive acceptance were unverified for that update because built-in browser use was disabled and the Mac locked. Source-level CSS contracts and DOM tests are not presented as a rendered audit.
- Publication: signed source commit [`d579153`](https://github.com/alo-exp/optimax/commit/d5791538f672a3e9858a349ff52eef268b4b2826) and [Actions run 42375920332](https://github.com/alo-exp/optimax/actions/runs/42375920332). CI reported 61 tests, 61 passes, zero failures and zero skips; build and deployment succeeded. Live checks verified all 29 files byte for byte, the new heading, removed credit, early theme script, parallel positioning and custom HTTP 404. No DNS changes were needed or made.


## Historical Circuit production homepage and complete CMF copy

This qualification predates preview removal and later Help, control and capture changes. Its file counts, preservation claims and test results describe that earlier candidate, not the current one; consult the independent checks for the candidate being evaluated.

The user selected the existing Circuit direction. A `gpt-6.1-sol` subagent at Max rewrote the supporting homepage narrative using the supplied CMF v3.0 guide. [MESSAGING.md](../site/MESSAGING.md) maps all 14 core components and eight companion sections, including justified compression and exclusions. The approved hero and subtitle were preserved in that promotion. Seven FAQs, a direct definition, scoped evidence, free-plugin versus model-usage charges, off controls and a first-session next step replaced the former supporting copy.

Observed qualification from `site/`:

- `rtk node --test tests/homepage-production.test.js`: both deployment fixtures first failed because the selected homepage stylesheet was absent; they passed after structural promotion. Before applying the revised copy, both failed on the expected old-title mismatch, then passed the complete accepted-copy contracts after integration.
- `rtk npm test`: 123 tests passed. At that qualification, historical preview copy tests used an attributable frozen body from commit 36f5533; their original assertions were retained at that qualification. The primary independently verified that fixture against the committed source.
- `rtk test npm run test:browser`: 138 cases passed across both deployment bases. Root coverage in those 138 cases included 320, 390, 768 and 1440 pixels in both themes, local fonts, fully visible installation controls, readable functional text, diagram clearance, all seven FAQ disclosures, actual clipboard behavior, theme persistence and focus contrast.
- Two classes of initial browser failures were test-model errors: reseeding storage on every reload and sampling the button fill instead of its offset focus outline. Those corrected tests preserved checks for explicit-choice persistence and the 3:1 focus-contrast requirement. These were test corrections, not production defect repairs.
- That build output had 57 files. All 54 previously published non-homepage files were byte-for-byte unchanged; `index.html` changed and `assets/homepage.css` plus `assets/homepage-theme.js` were added. Existing Help, all four historical previews, source fonts and shared controls remained intact in that build.
- The earlier qualification recorded fourteen ignored local captures covering full pages, native desktop/mobile openings, proof, all expanded FAQ answers and installation. This historical count does not establish their present availability. Rendered screenshots and public HTTP delivery checks have separate consumers; the former do not establish the latter.

At that qualification, publication remained gated by the [website workflow](https://github.com/alo-exp/optimax/actions/workflows/pages.yml), followed by HTTP byte comparison against the qualified build. That website qualification did not extend the dated plugin-host evidence above and did not establish Claude live acceptance, universal host support or measured time/cost savings.
