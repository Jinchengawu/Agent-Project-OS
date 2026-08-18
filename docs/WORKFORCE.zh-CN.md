# Agent HR 与人才治理

[English](WORKFORCE.md)

Agent HR 让整个 Harness 的 Agent 人才能持续演进，同时不会把模型名或某次客户端会话误当作 Agent 身份。Agent 记录引用运行时中立的角色，并用仓库路径、Git commit 与 SHA-256 标识 Prompt、Skill 或 bundle 版本。

## 不变量

- 一个 Agent 最多有一个 active release 和一个 candidate release。
- 候选版本必须具备同一 Agent 的通过评测。
- 候选 Agent、独立 Reviewer 与晋升批准人必须是三个不同身份。
- 晋升前重新校验候选资产 digest，并把旧 active release 保留为回滚点。
- 回滚前重新校验旧资产；仍有 active 角色分派依赖时，禁止退役 Agent。
- 生产、权限升级、公开发布和 Agent 晋升仍是人工权威门禁。

## 版本闭环

```sh
agent-project role add --role-id project-pm --name "Project PM" \
  --purpose "监管一个项目" --authority submit_supervision_report

agent-project agent add --agent-id agent:service-pm --name "Service PM" \
  --role-id project-pm --release-id service-pm-v1 \
  --asset-path agents/service-pm.md --asset-commit abc123 \
  --asset-sha256 <sha256>

agent-project agent evaluate --evaluation-id service-pm-eval-v2 \
  --agent-id agent:service-pm --reviewer agent:hr-reviewer \
  --score 4 --outcome passed --evidence-ref evidence:eval-v2

agent-project agent propose-upgrade --proposal-id service-pm-upgrade-v2 \
  --agent-id agent:service-pm --release-id service-pm-v2 \
  --asset-path agents/service-pm-v2.md --asset-commit def456 \
  --asset-sha256 <sha256> --evaluation-id service-pm-eval-v2 \
  --proposed-by agent:service-pm

agent-project agent promote --proposal-id service-pm-upgrade-v2 \
  --approved-by agent:hr-approver
```

`agent-project workforce review` 会生成不可变人才复盘记录。大盘只投影 Agent 生命周期、角色、active release 与 candidate release。

Agent Project OS 拥有中立记录和状态机。AI-PMO 这类能力仓库可以继续拥有具体角色、Skills、Prompts、评测集与版本内容；双方通过路径、版本、commit、digest、证据和 CLI/Schema 兼容接口集成，不复制源码。
