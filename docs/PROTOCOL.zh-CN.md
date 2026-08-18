# 协议与 CLI

[English](PROTOCOL.md)

## 仓库契约

```text
AGENTS.md
.agent-project/
├── manifest.json
├── policy.json
├── tasks/
├── evidence/
├── decisions/
├── handoffs/
├── inbox/
├── receipts/
└── events/
```

每条 JSON 记录都声明 `protocol_version`。核心 Schema 标识符使用稳定 URL，随包 Schema 文件可离线使用。Portfolio 根目录增加 `portfolio.json`；项目路径应使用相对路径，保证可移植性。

## 命令面

```text
agent-project init
agent-project validate
agent-project project add|list|show
agent-project task create|update|submit|accept|reject
agent-project evidence add
agent-project decision propose|accept|reject|supersede
agent-project handoff create|validate
agent-project affected
agent-project adapter render|install|uninstall|doctor
agent-project index rebuild
agent-project status
```

全局 `--root` 选择项目/Portfolio，`--json` 输出机器可读结果。所有写命令支持 `--dry-run`。成功返回 `0`；校验完成但记录无效返回 `1`；命令或前置条件错误返回 `2`。

## Runtime 身份

写入可以包含：

```json
{
  "runtime": "codex",
  "client_version": "1.2.3",
  "model_id": "example-model",
  "provider_hint": "example-provider"
}
```

只有 `runtime` 和 `client_version` 必填。`model_id` 与 `provider_hint` 只是元数据，不构成授权。

## 提案与接纳

`task submit` 创建变更请求，但不改变任务接纳态。`task accept` 会确认请求仍以当前 `updated_at` 为基线；过期提案失败，必须重新提交。`task reject` 记录复核结果，但不应用 patch。

直接使用 `task update`、`decision accept` 和 evidence `--accepted`，表示人工或策略已授权。除非 policy 另有规定，客户端 Adapter 应优先提交 inbox 提案。

## 跨项目产物契约

跨项目回执标识：

- `producer` 与 `consumer` 项目 ID；
- 产物协议/版本；
- 生产者 Git commit；
- 产物 SHA-256；
- 证据引用；
- `pending`、`accepted` 或 `rejected` 状态。

E3 必须引用消费者为当前项目的已接纳回执。Portfolio 校验会拒绝把未接纳跨项目回执当成交付证据。

## 隐私与合并行为

不得保存凭据、完整对话、完整终端转储或无关 diff。应保存摘要与精确的文件/commit/digest 引用。事件与回执文件名必须唯一；独立写入者不得共同追加同一个 JSONL 文件。
