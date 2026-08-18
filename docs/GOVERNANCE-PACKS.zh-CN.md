# 能力包与治理集成

[English](GOVERNANCE-PACKS.md)

Agent Project OS 内置运行时中立的 CEO/PMO 与 Agent HR 治理。外部能力仓库可以提供具体角色、Skills、Prompts 和评测内容，但不能成为第二真源。

## AI-PMO 能力包

AI-PMO 风格仓库拥有具体 PMO/HR 角色定义、Skills、Prompts、评测集及其版本历史。Agent Project OS 拥有中立组织、报告、评测、晋升和 Cadence 契约。双方通过已发布 Schema/CLI 版本、路径、Git 标识、SHA-256、验证结果和接纳回执集成。

双方都不得把项目任务账本复制到另一份 canonical 存储，不得静默接纳项目工作，也不能把“生成报告”当成 E3/E4 证据。

## AI-Work-Watcher Bridge

工作流观测桥可以观测提示词/任务结构并提出改进建议。它既不拥有任务状态，也不拥有接纳权。脱敏观测应独立保存，项目变更必须通过标准 inbox 契约提交。

桥接名称与接口保持通用；历史产品命名和私有仓库内部实现不属于本公开项目。

## 集成规则

```text
Agent Project OS Schema/CLI -> 版本化治理接口 -> 能力包
能力包 -> 资产版本/评测证据 -> Agent HR 复核路径
```

各包之间不复制源码；兼容性由协议/包版本声明，并通过契约测试验证。
