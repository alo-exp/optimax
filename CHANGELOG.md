# Changelog

## 0.2.0 (prerelease)

- Prepare an unpublished candidate bundling Review Ladder with Optimax in the plugin archive; the standalone archive remains Optimax-only.
- Add the explicit review and repair ladder, Opus Max policy, and audit corrections to the skill instructions.
- Qualify candidate release metadata and bundled runtime assets with local automated checks. Published catalog resolution, live discovery of the new command, complete ladder execution, Claude acceptance and native Windows execution remain separate pending gates.

## 0.1.1 (prerelease)

- Add a Windows-compatible performance-controller lock path and filesystem handling while retaining POSIX directory locking.
- Keep Windows lock files in the resolved user profile cache so controllers with different temporary-directory settings share one project lock.
- Retry Windows lock acquisition only for contention; propagate permanent lock errors without retrying indefinitely.
- Add portable regression coverage for Windows lock selection, error handling, cleanup and cross-process coordination. Native Windows execution remains untested; Claude live acceptance remains deferred.

## 0.1.0

- Introduce Optimax branding and a single canonical skill shared by thin plugin packages.
- Provide deterministic allowlisted standalone and plugin release archives.
- Preserve historical policy identifiers, event history, and project/user ledger locations.
