# Compatibility Matrix

[中文](COMPATIBILITY.zh-CN.md)

Status as of 2026-08-14. “Protocol” means the common baseline; client-only enhancements are listed separately.

| Surface | Support | Protocol baseline | Enhancements / limits |
|---|---|---|---|
| Python 3.9–3.13 | Supported | CLI, Schema, index | Runtime uses the standard library; tests add `jsonschema` |
| macOS | Supported | Full local CLI | CI matrix target |
| Linux | Supported | Full local CLI | CI matrix target |
| WSL | Preview | Expected Linux behavior | Not a release-blocking matrix target in v0.1 |
| Codex | Supported | AGENTS, Skill, records, validation | Worktrees/subagents are optional enhancements |
| Claude Code | Supported | AGENTS import, Skill, records, validation | Lifecycle Hooks normalized; Agent Teams optional |
| DeepSeek Harness | Preview | Rules, records, validation, event bridge | Pinned to `0.1.0-rc.5` / `47f9438`; breaking changes expected |

Deterministic adapter golden, preservation, idempotency, uninstall, and event-normalization tests are part of CI. Live client smoke status is recorded in release evidence, not permanently claimed by this matrix.
