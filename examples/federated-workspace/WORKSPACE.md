# Synthetic federated workspace / 合成联邦工作区

This fixture contains no real projects or paths. It demonstrates three autonomous repositories with different technology stacks:

- `contracts` (Python): produces `orders@2` and has accepted E2 verification.
- `service` (Node.js): consumes `orders@2`, records an accepted cross-project receipt and E3, then produces `service-api@2`.
- `client` (Rust): consumes `service-api@2` and remains blocked on a dependency risk gate.

The service handoff switches from a Codex runtime identity to Claude Code. The client handoff targets DeepSeek Harness, which remains preview-only.

本夹具不包含任何真实项目或路径。三个自治仓库分别使用 Python、Node.js 与 Rust；它展示跨项目接口变更、E2 校验、E3 消费者接纳、阻塞分类，以及 Codex → Claude Code → DeepSeek Harness 的跨客户端交接。

Validate and query it from this directory:

```sh
agent-project validate
agent-project affected --project-id contracts --json
agent-project index rebuild --json
```
