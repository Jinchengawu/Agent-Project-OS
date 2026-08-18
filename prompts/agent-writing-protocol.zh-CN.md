# Agent 写入协议提示词

[English](agent-writing-protocol.md)

当模型或客户端不能直接加载共享 Skill 时，使用以下提示词。

```text
你正在参与一个由 Agent Project OS 管理的仓库。

Git 跟踪的项目记录是可移植事实源；对话、客户端任务列表和模型记忆只属于执行上下文。

工作前：
1. 阅读 AGENTS.md、.agent-project/manifest.json、policy.json、相关任务、已接纳决策和最新交接。
2. 运行 agent-project status --json 与 agent-project validate --json。
3. 明确结果、验收标准、受影响项目和人工批准门禁。

工作中：
- 分开记录 runtime、client_version、model_id 与 provider_hint。
- 除非 policy 明确授权直接接纳，Agent 发起的状态变化必须提交到 .agent-project/inbox。
- 没有已接纳的 E2 或更高级证据，不得进入 done。
- 严格区分 E0 声明、E1 产物、E2 确定性验证、E3 消费者接纳和 E4 外部结果。
- 不可逆、生产、权限、资金或公开发布动作前必须停止并取得人工批准。
- 不得保存凭据、私有路径、完整对话或完整终端输出。

结束时：
1. 运行项目的确定性验证。
2. 只记录实际达到的证据等级。
3. 更新或提交任务状态；若工作在其他环境继续，创建边界清晰的交接。
4. 运行 agent-project validate --json 与 agent-project status --json。
5. 分开报告接纳态、待审提案、阻塞与外部结果。
```
