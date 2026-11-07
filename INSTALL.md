# Install Optimax

Use the unified Ālo Labs marketplace for a plugin installation. Catalog publication and host installation are separate gates; see the release's verification report for tested support.

## Codex plugin

```sh
codex plugin marketplace add alo-labs/agent-plugins
codex plugin add optimax@alo-labs-codex
codex plugin list --json
```

Then invoke `$optimax on`, `$optimax status`, or `$optimax off` in the Codex conversation.

## Claude Code plugin

Run these commands in Claude Code:

```text
/plugin marketplace add alo-labs/agent-plugins
/plugin install optimax@alo-labs
/optimax:optimax status
/optimax:optimax on
```

Use `/optimax:optimax off` to disable the policy. Claude live acceptance is deferred until Tuesday 10 November 2026 at 14:00 Australia/Sydney; these instructions are statically checked, not a live Claude result.

## Standalone skill fallback

From an Optimax source checkout, obtain the matching `optimax-skill.zip` release asset and run:

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

Installation does not enable the session policy. Establish your actual stable user ID and canonical project root on first use; private learning stays under that project's `model-perf/` directory. Skill off does not uninstall the plugin or change native mode settings. A sandbox that cannot write your host configuration or skill directory cannot complete a global installation; run the appropriate command in an authorized host session.
