# 周期监督与跨客户端派工

[English](CADENCE.md)

Agent Project OS 不运行后台 daemon。它只做确定性的到期计算、幂等运行计划和有限重试记录，再由 Codex Automations、cron、CI 或其他获批调度器负责唤醒。

```sh
agent-project cadence due --as-of 2026-08-18T01:00:00Z
agent-project cadence plan --run-id week-34 \
  --window-start 2026-08-18T00:00:00Z \
  --window-end 2026-08-25T00:00:00Z \
  --as-of 2026-08-18T01:00:00Z
agent-project cadence record --run-id week-34 \
  --action-id supervision-service-2026-08-18T00-00-00Z \
  --result succeeded --result-ref dispatch:service-week-34
agent-project cadence close --run-id week-34 --outcome completed
```

组织、时间窗口和边界会生成稳定 dedupe key。同一窗口重复触发时返回既有 run，不会产生第二份运行记录。每个 action 最多记录三次尝试；只有所有 action 都成功，run 才能关闭为 completed。外部调度器不能借此接纳报告、晋升 Agent 或跨过人工门禁。

PMO 创建 dispatch envelope 后，可以只渲染客户端入口，而不启动客户端：

```sh
agent-project adapter render-dispatch --dispatch-id service-week-34 --adapter codex
agent-project adapter render-dispatch --dispatch-id service-week-34 --adapter claude-code
agent-project adapter render-dispatch --dispatch-id service-week-34 --adapter deepseek-harness
```

三份入口携带相同目标、产物、验收标准、负责人和截止时间。客户端差异只留在 Adapter seam；DeepSeek Harness 继续固定兼容点并标注 Preview。
