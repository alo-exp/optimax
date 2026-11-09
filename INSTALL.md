# Install Optimax

Use the unified Ālo Labs marketplace for a plugin installation. This checkout targets the unpublished v0.2.0 prerelease candidate. The commands below resolve the published catalog; candidate catalog publication remains pending. Catalog publication and host installation are separate gates; see the [verification report](docs/VERIFICATION.md) for tested support.

## Codex plugin

```sh
codex plugin marketplace add alo-labs/agent-plugins
codex plugin add optimax@alo-labs-codex
codex plugin list --json
```

Then invoke `$optimax on`, `$optimax status`, or `$optimax off` in the Codex conversation. This source checkout's plugin archive also bundles Review Ladder at `skills/review-ladder/`; after host discovery, invoke `$review-ladder` with a bounded review scope. Publication and live discovery of the added skill remain unverified.

## Claude Code plugin

Run these commands in Claude Code:

```text
/plugin marketplace add alo-labs/agent-plugins
/plugin install optimax@alo-labs
/optimax:optimax status
/optimax:optimax on
```

Use `/optimax:optimax off` to disable the policy. Claude live acceptance is deferred until Tuesday 10 November 2026 at 14:00 Australia/Sydney; these instructions are statically checked, not a live Claude result.

After the host discovers the bundled review skill, invoke `/optimax:review-ladder` with a bounded review scope. Any shorter alias depends on the host. The plugin archive contains both Optimax and Review Ladder; adding source files or rebuilding an archive does not register the new skill in an existing session.

## Standalone skill fallback

The `optimax-skill.zip` archive and the installer below remain Optimax-only. They do not include or install Review Ladder; use the plugin package for both skills.

From this matching v0.2.0 candidate source checkout, build the archive with `python3 build_release.py --output dist`, then use `dist/optimax-skill.zip` as the archive path below. The v0.2.0 candidate has not been published; [v0.1.1 downloads](https://github.com/alo-exp/optimax/releases/tag/v0.1.1) belong to the historical release. Run:

```sh
mkdir -p "$HOME/.codex/skills"
python3 skills/optimax/scripts/install_local.py --archive /path/to/optimax-skill.zip
```

For Claude's standalone skill directory:

```sh
mkdir -p "$HOME/.claude/skills"
python3 skills/optimax/scripts/install_local.py --archive /path/to/optimax-skill.zip --dest "$HOME/.claude/skills/optimax"
```

The installer validates the archive, requires an existing parent, refuses existing destinations and installs runtime files only. It does not overwrite a previous installation. Inspect an existing destination before updating. Refresh the host's discovery after installation. Avoid simultaneously loading standalone and packaged copies as separate orchestrators.

Keep the destination parent and new installation tree under exclusive control until installation finishes. Concurrent replacement of directories is unsupported; pathname checks do not provide confinement against another actor mutating the tree.

Installation does not enable the session policy. Establish your actual stable user ID and canonical project root on first use; private learning stays under that project's `model-perf/` directory. Skill off does not uninstall the plugin or change native mode settings. A sandbox that cannot write your host configuration or skill directory cannot complete a global installation; run the appropriate command in an authorized host session.

On Windows, use an available Python 3 interpreter for the installer and controller. Controllers for the same project must share the same resolved user profile and be able to write its `~/.optimax/locks` cache. Network filesystems remain unsupported. Windows compatibility has portable regression coverage on POSIX; native Windows installation and execution remain untested.
