# 版本策略

[English](VERSIONING.md)

Agent Project OS 的 Python 包采用语义化版本；持久化记录采用显式协议版本。

- 包版本 `0.x`：公共 CLI 和 Adapter 细节可以变化，但必须提供迁移说明。
- 包版本 `1.x`：公共 CLI 的不兼容变化必须提升主版本。
- 核心记录的 `protocol_version`：仅在持久化语义或必填字段不兼容时变化。
- Schema 文件名是不可变契约，例如 `task-v1.schema.json`。破坏性记录变更必须新增 `task-v2`，不能暗中改写 v1 含义。
- Adapter 兼容固定点可在补丁版或次版本中变化，不需要修改核心协议版本。

读取方必须拒绝不支持的主协议版本；写入方必须输出明确声明的版本，不得猜测降级。派生索引可删除重建，因此不提供兼容承诺。

预发布格式：Python 元数据使用 PEP 440（`0.4.0a1`），可能的 Git 标签使用 SemVer 写法（`v0.4.0-alpha.1`）。当前工作候选没有 tag。创建 tag、GitHub Release 或发布包都是独立的人工批准动作。
