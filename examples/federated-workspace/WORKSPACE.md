# Synthetic AI engineering organization / 合成 AI 工程组织

This fixture contains no real projects or paths. It demonstrates a Founder/CEO/PMO organization over three autonomous repositories with different technology stacks:

- `contracts` (Python): produces `orders@2` and has accepted E2 verification.
- `service` (Node.js): consumes `orders@2`, records an accepted cross-project receipt and E3, then produces `service-api@2`.
- `client` (Rust): consumes `service-api@2` and remains blocked on a dependency risk gate.

Each project has one accountable PM. Synthetic child-PM reports show PMO acceptance and a client blocker raised into the CEO exception queue. Agent HR records a reviewed service-PM release upgrade with a rollback point. The service handoff switches from a Codex runtime identity to Claude Code; the client handoff targets DeepSeek Harness, which remains preview-only.

本夹具不包含任何真实项目或路径。Founder/CEO/PMO 组织管理三个自治仓库，每个项目只有一个 accountable PM；子 PM 报告展示 PMO 接纳和进入 CEO 例外队列的客户端阻塞，Agent HR 记录带回滚点的人才版本晋升。三个仓库分别使用 Python、Node.js 与 Rust，并保留跨项目接口变更、E2、E3 以及 Codex → Claude Code → DeepSeek Harness 交接。

Validate and query it from this directory:

```sh
agent-project validate
agent-project affected --project-id contracts --json
agent-project index rebuild --json
agent-project dashboard build --as-of 2026-08-18T12:00:00Z --json
```
