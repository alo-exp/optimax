# Native Codex acceptance

Checked 2026-11-07 against published Optimax v0.1.0, source `54540db3ea74374677438995d9fce83b58e1441d`, from the unified Ālo Labs catalog at `bd142ccb3ecb5c0bb0572aedc5be76666a97c842`.

## Observed host behavior

Codex CLI `0.166.0-alpha.6` registered `alo-labs/agent-plugins`, installed and enabled `optimax@alo-labs-codex`, and listed the pinned v0.1.0 plugin. This replaced the user's previous local mapping for that marketplace with explicit authorization. Independent before/after comparison established that other marketplace registrations and installed plugins were preserved. All 13 installed runtime skill files matched the released source bytes.

A real native `gpt-6.1-terra` session with `medium` reasoning discovered the installed `optimax:optimax` skill from `$optimax status`, without a supplied skill path. Native runtime metadata established the effective model and effort. In a disposable project with a fixture identity, the observed status sequence across controller invocations was disabled → enabled → enabled → enabled → disabled → disabled → enabled → enabled. Explicit enable and disable, idempotent enable, and same-session-ID recovery across separate controller processes passed. Recommendations remained unapplied, and no real task assessments were manufactured by the fixture.

A second native `gpt-6.1-terra` session with `low` reasoning discovered the same installed plugin and returned disabled status under its distinct actual thread ID. The fixture ledger SHA-256 remained unchanged. This establishes fresh-session default behavior; it does not establish recovery after context compaction.

## Evidence and limits

The primary agent independently inspected native runtime banners, installed-cache skill reads, actual controller output, configuration/plugin snapshots, and the fixture ledger hash. Private raw transcripts and configuration snapshots are excluded from the release and public repository.

These tests establish the observed client and release behavior. They do not establish every Codex client/version, native Ultra operation, hidden-worker attribution, compaction recovery, performance savings or any Claude execution. Preservation contracts for supplied native context also have automated core coverage, which is separate from native-mode acceptance. Claude acceptance is deferred as described in [CLAUDE-ACCEPTANCE.md](CLAUDE-ACCEPTANCE.md).
