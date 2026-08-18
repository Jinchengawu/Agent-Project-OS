# 组织与 PMO 治理

[English](ORGANIZATION.md)

Agent Project OS 用本地文件表达 AI 工程组织，但不会把组织仓库变成所有项目任务账本的复制品。

```text
Founder
└── Agent CEO
    ├── PMO
    │   ├── 项目 PM A → 项目 A 的工程 Agent 与证据
    │   ├── 项目 PM B → 项目 B 的工程 Agent 与证据
    │   └── 项目 PM N → 项目 N 的工程 Agent 与证据
    └── Agent HR → 角色、评测、版本、晋升与退役
```

## 所有权边界

组织根仓库拥有工程注册、优先级、accountable PM 分派、监督派工、不可变子 PM 报告、PMO 评审、Portfolio Review 与 CEO 例外队列。各项目仓库继续拥有任务、证据、决策、交接和领域状态。报告只保存摘要与证据指针，不复制任务账本。

每个 active 项目必须且只能有一个 accountable PM。PM 可以提交报告，但不能评审自己的报告；最终接纳由 PMO 或 Founder 记录。报告声称 `done` 时至少要有一条证据引用；若项目路径是 Git 仓库，提交的 commit 必须与当前 HEAD 一致。

## 最小闭环

```sh
agent-project org init --organization-id studio --name "Studio" \
  --founder human:founder --ceo-agent-id agent:ceo --pmo-agent-id agent:pmo

agent-project project add --project-id service --path projects/service \
  --owner human:founder --project-priority P1 \
  --verification "python -m unittest" --supervision weekly \
  --next-due-at 2026-08-24T01:00:00Z

agent-project project assign-pm --assignment-id service-pm \
  --project-id service --pm-agent-id agent:service-pm

agent-project supervision dispatch --dispatch-id service-week-34 \
  --project-id service --objective "核对当前证据与阻塞" \
  --expected-output "有边界的子 PM 报告" --acceptance "引用当前 commit" \
  --due-at 2026-08-25T01:00:00Z

agent-project supervision submit --report-id service-report-34 \
  --dispatch-id service-week-34 --summary "确定性校验已通过" \
  --project-commit abc123 --reported-status waiting_review \
  --next-acceptance "消费者接纳契约" \
  --evidence-ref evidence:service-e2 --submitted-by agent:service-pm

agent-project supervision accept --review-id service-review-34 \
  --report-id service-report-34 --reviewed-by agent:pmo
agent-project portfolio review --review-id portfolio-week-34 \
  --as-of 2026-08-25T02:00:00Z
```

报告被接纳后，系统会按项目声明的 IANA 时区推进下一次日、周或月监管时间。月度周期按本地日历计算，并在转回 UTC 前处理夏令时变化。

## CEO 例外队列

Portfolio Review 和只读大盘会列出缺 PM、报告缺失或被拒绝、存在明确阻塞的 active 项目。它们不会静默修改优先级，也不会代替项目验收。`P0`–`P3` 只是组织路由字段，不是业务价值证据。
