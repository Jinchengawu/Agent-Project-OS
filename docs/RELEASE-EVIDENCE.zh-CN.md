# v0.1 Release Candidate 证据

[English](RELEASE-EVIDENCE.md)

证据日期：2026-08-14。机器可读摘要位于 `release/smoke-results-v0.1.json`。

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

这些证据不授权创建公开仓库、push、tag 或发布包。README/展示复核与最终人工批准完成后，发布动作仍需单独授权。
