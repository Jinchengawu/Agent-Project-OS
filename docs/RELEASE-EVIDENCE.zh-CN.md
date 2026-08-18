# Release Candidate 证据

[English](RELEASE-EVIDENCE.md)

## v0.4.0a1 本地候选 — 2026-08-18

本地观测结果：

- 33 项集成与契约测试通过，覆盖 CEO/PMO 监督、Agent HR 晋升/回滚、Cadence 幂等、迁移、投影和三端派工渲染。
- 28 份 Draft 2020-12 Schema 全部可加载；每个新增 Governance/Workforce/Cadence 契约都有正例、缺字段与不兼容版本样例。
- 合成组织由三个项目、五个 Agent、一次已复核人才升级、两份已接纳 PM 报告和一个 CEO 阻塞例外组成，并通过校验。
- 规模门禁可重建 30 个项目、50 个 Agent、29 个传递下游项目、30 个到期项与只读大盘。
- `scripts/release_gate.py`、隐私、双语配对、Python 编译、DeepSeek Harness JavaScript 语法、源码包、wheel 构建和隔离 wheel CLI smoke 在本机 Python 3.11/macOS 通过。

这不是 `0.5.0b1` 证据：尚未运行连续两轮私有只读影子周期。也不是 `1.0.0` 证据：没有私有项目切换到单真源。README 修正仍在等待本轮 Showcase Proposal 批准。

## 历史 v0.1 候选 — 2026-08-14

机器可读客户端 smoke 摘要位于 `release/smoke-results-v0.1.json`。

## 确定性测试

- 核心生命周期、过期提案、证据门禁、决策、交接、联邦、循环/接口/回执拒绝、索引重建、Adapter、隐私和合成工作区测试通过。
- 安装 `test` extra 后，Draft 2020-12 正例、缺字段、非法状态、伪造 E2/E3 和不兼容版本样例全部运行。
- Adapter golden、已有配置保留、幂等、卸载恢复和归一化事件校验通过。
- DeepSeek Harness bundle JavaScript 在固定预览兼容点通过语法检查。

## 真实客户端 Smoke

两个隔离的合成项目都完成了“创建 → 验证 → E2 → done”闭环：

| 客户端 runtime | 客户端版本 | 实际 model ID | 结果 |
|---|---|---|---|
| Codex | `0.147.0-alpha.6.5` | `gpt-5.6-sol` | 通过 |
| Claude Code | `2.1.181` | `deepseek-v4-pro` | 通过 |

Claude Code 这条结果直接验证了身份规则：客户端 runtime 与模型必须是两个字段。

本机未安装 DeepSeek Harness，且没有可用凭据。其 keyless bundle/config/Schema/语法路径通过，Adapter 继续标记为 `preview`；本项目不声称完成 DSH 真实闭环。

记录未保留 session ID、完整对话、含私有上下文的提示词、项目绝对路径、凭据或费用数据。

## 剩余人工门禁

远程仓库来自此前已明确批准的 push。本证据不授权再次 push、创建 tag、GitHub Release、发布包或迁移私有项目。README/展示复核完成后，这些动作仍需单独人工批准。
