# Runtime Adapters

[中文](ADAPTERS.zh-CN.md)

Adapters translate client conventions into Agent Project OS without changing the core Schema.

## Common guarantee

All supported adapters can expose shared project rules, point an Agent at task/evidence/handoff commands, preserve runtime identity, and run deterministic validation. Worktrees, subagents, Agent Teams, plugins, and UI integration are optional client enhancements, not cross-client parity promises.

## Codex

- Shared instructions: `AGENTS.md`.
- Shared workflow: `.agents/skills/agent-project-os/SKILL.md`.
- Metadata: `.agent-project/adapters/codex.json`.
- No Codex task or chat is treated as core truth.

## Claude Code

- `CLAUDE.md` contains a managed block that imports `@AGENTS.md`; existing Claude-only notes remain outside the block.
- The shared Skill is mapped to `.claude/skills/agent-project-os/SKILL.md`.
- `SessionStart` and `Stop` hooks write minimal normalized lifecycle events. They do not persist prompts, tool arguments, terminal output, or transcripts.
- Existing `.claude/settings.json` keys are preserved and restored on uninstall.

## DeepSeek Harness

- Status: **preview** because upstream explicitly declares developer preview and compatibility-breaking changes.
- Pinned compatibility point: `0.1.0-rc.5`, commit `47f943859bef60e4160492346772ded9b24f765a`.
- Rendered output is an out-of-tree Cordis bundle under `.dsh/agent-project-os-bundle` with `dsh.bundle.patch` metadata.
- Install it into an explicit profile with `dsh plugin --profile <profile> add ./.dsh/agent-project-os-bundle`, then inspect `dsh --profile <profile> --dump-config`.
- The plugin normalizes session, turn, and tool lifecycle events without storing tool payloads.

When upstream breaks, change and retest only this Adapter. Do not add DSH profile, bundle, Cordis, or event names to core records.

## Installation safety

Project-local rendering is the default:

```sh
agent-project adapter render --adapter all
```

User-level writes require explicit `--user`. Existing files are backed up, generated content is hashed, repeated installs are idempotent, and uninstall restores original content. If a generated-only managed file changes after installation, the CLI refuses to overwrite or delete it.

```sh
agent-project adapter install --adapter codex --user --dry-run
agent-project adapter install --adapter codex --user
agent-project adapter uninstall --adapter codex --user
agent-project adapter doctor --adapter all
```

Official references: [Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [Codex Skills](https://learn.chatgpt.com/docs/build-skills), [Claude Code memory](https://code.claude.com/docs/en/memory), [Claude Code Hooks](https://code.claude.com/docs/en/hooks), and [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness).
