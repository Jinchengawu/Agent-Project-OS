# Roadmap

[中文](ROADMAP.zh-CN.md)

## Release state

`0.1.0a1` is the pushed, untagged historical Project Kernel baseline. The current local working candidate is `0.4.0a1`; no tag, GitHub Release, or package publication is implied.

| Version gate | Outcome | Evidence state |
|---|---|---|
| `0.1.0a2` | Correct the product boundary: the Kernel is one layer of an organization OS | Implemented in architecture and method docs; README awaits a new Showcase approval |
| `0.2.0a1` | Founder/CEO/PMO/project-PM vertical loop | Implemented and covered by synthetic integration tests |
| `0.3.0a1` | Agent HR registry, evaluation, release, promotion, rollback, pause, retirement | Implemented and covered by synthetic integration tests |
| `0.4.0a1` | Due calculation, idempotent cadence runs, bounded retry records, three-client dispatch rendering | Implemented; current local candidate |
| `0.5.0b1` | Read-only dashboard, 30-project/50-Agent scale gate, two private shadow cycles | Dashboard and public scale gate implemented; two private cycles not performed, so beta gate is open |
| `1.0.0` | Freeze Schema/CLI, prove upgrade/rollback, and switch one non-critical private project to a single source of truth | Not started; requires separate private migration approval |

## Stable exclusions

V1 does not build team accounts, RBAC, cloud synchronization, a hosted SaaS, or an Agent runtime. The dashboard stays read-only and rebuildable. DeepSeek Harness remains Preview until its upstream contract stabilizes. The archived early Vercel concept under `docs/future/` is historical context, not current architecture.
