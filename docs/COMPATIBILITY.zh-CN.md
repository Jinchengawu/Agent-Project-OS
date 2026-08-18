# 兼容矩阵

[English](COMPATIBILITY.md)

状态日期：2026-08-14。“协议基线”指三端共同能力；客户端增强单独列出。

| 范围 | 支持级别 | 协议基线 | 增强/限制 |
|---|---|---|---|
| Python 3.9–3.13 | 正式支持 | CLI、Schema、索引 | Runtime 仅使用标准库；测试额外使用 `jsonschema` |
| macOS | 正式支持 | 完整本地 CLI | CI 矩阵目标 |
| Linux | 正式支持 | 完整本地 CLI | CI 矩阵目标 |
| WSL | 预览 | 预期与 Linux 行为一致 | v0.1 不作为发布阻断矩阵目标 |
| Codex | 正式支持 | AGENTS、Skill、记录、校验 | Worktree/subagent 为可选增强 |
| Claude Code | 正式支持 | 导入 AGENTS、Skill、记录、校验 | 生命周期 Hooks 已归一化；Agent Teams 可选 |
| DeepSeek Harness | 预览 | 规则、记录、校验、事件桥 | 固定 `0.1.0-rc.5` / `47f9438`；预期会破坏兼容 |

确定性 Adapter golden、已有配置保留、幂等、卸载和事件归一化测试属于 CI。真实客户端 smoke 状态写入每次发布证据，不在兼容矩阵中永久宣称。
