# Cadence and Cross-client Dispatch

[中文](CADENCE.zh-CN.md)

Agent Project OS does not run a background daemon. It deterministically calculates due supervision, creates an idempotent run plan, records bounded attempts, and lets Codex Automations, cron, CI, or another approved scheduler wake that plan.

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

The organization, time window, and boundaries produce a stable dedupe key. Repeating the same window returns the existing run; it never creates a second run. Each action accepts at most three recorded attempts. A completed run requires all planned actions to succeed. The scheduler cannot accept reports, promote Agents, or cross a human gate.

After PMO creates a dispatch envelope, render a client entry without launching the client:

```sh
agent-project adapter render-dispatch --dispatch-id service-week-34 --adapter codex
agent-project adapter render-dispatch --dispatch-id service-week-34 --adapter claude-code
agent-project adapter render-dispatch --dispatch-id service-week-34 --adapter deepseek-harness
```

The three files carry the same objective, outputs, acceptance criteria, assignee, and due time. Client-specific instructions stay at the Adapter seam. DeepSeek Harness remains pinned and marked Preview.
