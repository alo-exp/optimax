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

Use `/optimax:optimax off` to disable the policy. These instructions are statically checked; live Claude acceptance remains unverified. See the [Claude acceptance runbook](docs/CLAUDE-ACCEPTANCE.md) for its status and scope.

After the host discovers the bundled review skill, invoke `/optimax:review-ladder` with a bounded review scope. Any shorter alias depends on the host. The plugin archive contains both Optimax and Review Ladder; adding source files or rebuilding an archive does not register the new skill in an existing session.

Installation does not enable the session policy. Establish your actual stable user ID and canonical project root on first use; private learning stays under that project's `model-perf/` directory. Skill off does not uninstall the plugin or change native mode settings. A sandbox that cannot write your host configuration or skill directory cannot complete a global installation; run the appropriate command in an authorized host session.

On Windows, use an available Python 3 interpreter for the controller. Controllers for the same project must share the same resolved user profile and be able to write its `~/.optimax/locks` cache. Network filesystems remain unsupported. Windows compatibility has portable regression coverage on POSIX; native Windows installation and execution remain untested.
