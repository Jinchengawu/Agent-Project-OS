# 可选治理集成

[English](GOVERNANCE-PACKS.md)

Agent Project OS Core 有意保持单仓库即可独立使用。可选包可以消费稳定接口，但不能成为第二真源。

## AI-PMO Governance Pack

AI-PMO 风格治理包可以增加 Portfolio 报告、子项目报告、E0–E4 门禁、阻塞对账与组合接纳。它通过已发布 Schema 版本、`agent-project --json`、Git 标识、验证结果和接纳回执集成。

它不得把项目任务账本复制到另一份 canonical 存储，不得静默接纳项目工作，也不能把“生成报告”当成 E3/E4 证据。

## AI-Work-Watcher Bridge

工作流观测桥可以观测提示词/任务结构并提出改进建议。它既不拥有任务状态，也不拥有接纳权。脱敏观测应独立保存，项目变更必须通过标准 inbox 契约提交。

桥接名称与接口保持通用；历史产品命名和私有仓库内部实现不属于本公开项目。

## 集成规则

```text
Core Schema/CLI -> 版本化证据接口 -> 可选治理包
可选治理包 -> 变更请求/回执 -> Core 复核路径
```

各包之间不复制源码；兼容性由协议/包版本声明，并通过契约测试验证。
