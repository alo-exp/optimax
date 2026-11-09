# Platform model selection

Checked 2026-11-07. Interfaces, account access, model versions, and effort support change. At use time, prefer the runtime's actual capability listing and official documentation over this dated snapshot. A skill is instructions; it cannot add a model selector or make unsupported calls possible.

## Shared rules

On each explicit activation, use the bounded [instruction audit](calculator.md#instruction-audit-on-activation) and host semantic review to identify applicable restrictions before selecting helpers. Actual host settings and governing instructions determine applicability; candidate discovery is not proof of loading.

Select helpers from the host's ladder, independently of the Orchestrator model family. A user-selected Claude Orchestrator uses the Claude helper ladders; a Codex Orchestrator uses the Codex helper ladders. Do not mix providers or invoke an external paid API merely because a requested rung is missing.

Resolve the latest available version within Haiku, Sonnet, Opus, Terra, Sol, or Astra as applicable. Preserve explicit user version pins. Record the exact requested model ID and effort at dispatch, and the verified effective pair only when an actual receipt establishes it. A family alias or a requested setting alone does not prove what ran. Use stable versions unless the user explicitly permits previews. Newer unrelated families do not enter the ladder automatically.

If the runtime exposes only an alias, use it only when official mapping or launch metadata establishes its exact version. If the actual version or effort remains unverifiable, report that limit and exclude the result from performance windows. Do not label inherited defaults as an explicitly selected rung.

Discover model and effort support before launch. If a pair is unsupported or inaccessible, skip upward to the nearest supported rung and report a capability fallback. If none exists, report the exact blocker. A transient network failure is not evidence that a rung is unsupported. A later availability change must not rewrite previous decisions. Start a fresh epoch when the resolved version changes.

Select model and effort on the **helper invocation or helper definition**. Never use a session-wide `/model`, `/effort`, global environment override, or parent config edit to simulate per-helper settings. Avoid persistent agent-definition changes unless necessary and authorized. Do not reuse a resumed helper if its retained model/effort would differ from the newly selected rung.

Use [native-mode integration](native-modes.md) for direct, Codex native, and Claude Ultracode stage contracts. Native-mode labels do not select models. Prepare a run through the durable controller, apply only fields accepted by the actual interface, and obtain an effective receipt when exposed. If the native path lacks supported requested controls for the required pair or has a known conflicting override, use a supported direct helper. Missing effective receipts alone do not block permitted dispatch: disclose requested-only attribution and exclude that result from learning. If neither path can request the pair, report the capability blocker; do not automatically move substantive work to the root. Keep opaque runtime workers outside policy learning and disclose that coverage.

## Claude

The target families are Haiku 5.5, Sonnet 5.5, and Opus 5.5, or their latest available successors within the same family. Resolve actual API/provider identifiers from the runtime; do not construct IDs from marketing names. Examples documented for Anthropic include `claude-opus-5-5`; gateways and cloud providers can use deployment identifiers instead.

Claude Code supports helper `model` and `effort` fields, with explicit per-invocation effort on supported clients. Prefer a non-fork helper with both settings specified. The official documentation states that per-invocation effort requires Claude Code v2.1.292 or later, and Haiku 5.5 requires v2.1.293 or later. These are dated compatibility checks, not an instruction to update the user's client.

For a supported Agent tool, use its actual schema: typically `model: "haiku"`, `"sonnet"`, or `"opus"`, plus `effort: "low" | "medium" | "high" | "xhigh" | "max"`. Resolve aliases and verify effective settings. A configured helper definition can supply `model` and `effort` when the invocation schema cannot. Do not send invented fields to a tool.

The docs list all five effort levels on Haiku/Sonnet/Opus 5.5. Older models and account policies can differ. Claude Code can silently reduce unsupported effort, and `CLAUDE_CODE_EFFORT_LEVEL` can override a helper's effort. Verify the effective effort; if a requested Max actually ran at High, record High and do not count it as a Max result. Report the mismatch and use a compatible invocation without changing the Orchestrator's settings.

Claude chat/Cowork surfaces may not expose controllable model/effort pairs for every helper. Check the actual tools. If no eligible Advisor can be selected, leave dependent planning/design unfinalized and explain the blocker. Do not promise automatic optimization on an interface that cannot select the models.

For Ultracode Workflow stages, verify the live schema separately: direct Agent support does not prove Workflow exposes an equivalent effort argument. The [SDK WorkflowInput](https://code.claude.com/docs/en/agent-sdk/typescript#workflow) describes script, name, scriptPath and args, not a flat model/effort/prompt helper call. The unsupported flat `claude-workflow` adapter route is not available; direct `claude-agent` remains supported. Use a controller bridge to preselect stages and collect receipts; do not import Python/filesystem operations into restricted Workflow JavaScript. This package does not claim universal native interception or verified live Claude execution.

Claude child skills are not automatically inherited, and configurable child spawn depth does not give the root per-worker control. Official sources: [Claude Code subagents](https://code.claude.com/docs/en/sub-agents), [model and effort configuration](https://code.claude.com/docs/en/model-config), [model identifiers](https://platform.claude.com/docs/en/about-claude/models/overview).

## Codex

Current target IDs verified in this environment are `gpt-6.1-terra`, `gpt-6.1-sol`, and `gpt-6-astra`; resolve the latest available successors within each family at use time. Do not invent a `gpt-6.1-astra` identifier. Local metadata supports the selected Executor Terra Low/Medium/High and Sol Medium/High/XHigh/Max pairs, plus Advisor Sol XHigh/Sol Max/Astra Max. These dated local capabilities do not prove another installation's access.

When the exposed subagent API accepts per-run overrides, pass the exact `model` and `reasoning_effort` explicitly. On hosts where full-history forks inherit the parent's configuration and reject overrides, use a fresh-context launch such as `fork_turns: "none"` and supply a self-contained brief. Inspect the actual tool schema rather than assuming this parameter exists everywhere.

For configuration-based hosts, official Codex custom agent TOML definitions use `model` and `model_reasoning_effort`; explicit spawn overrides and inherited skills are documented separately. Scope those settings to the helper. Do not confuse the config key with a tool parameter named `reasoning_effort`. Do not change the main conversation's model or reasoning level. If configured helper roles or spawn overrides are unavailable, report the capability limit.

For example, a Medium-context Codex consultation starts at Sol XHigh; High requires at least Sol Max, and Super High requires Astra Max. A higher performance-selected rung remains valid. These are distinct helper invocations; inheriting a Sol High Orchestrator does not meet the requirement. Performance evidence may adjust the track within the current context floor. If the required pair is unavailable, only an eligible higher fallback may substitute; at the ceiling, report a blocker. Governing model policy may restrict this skill; disclose that restriction.

ChatGPT Ultra's proactive delegation and local Codex delegation are different surfaces: local Codex delegates when explicitly requested or directed by project or skill instructions. Do not infer feature activation, stage ownership, or dispatch route from the subscription name.

Official source: [Codex subagents and model/reasoning selection](https://developers.openai.com/codex/multi-agent/).
