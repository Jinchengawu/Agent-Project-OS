# Runtime Adapters

[English](ADAPTERS.md)

Adapter 把客户端约定翻译为 Agent Project OS，但不改变核心 Schema。

## 共同保证

所有支持的 Adapter 都能暴露共享项目规则，引导 Agent 使用任务/证据/交接命令，保留 runtime 身份，并运行确定性校验。Worktree、subagent、Agent Teams、plugins 和 UI 集成属于端侧增强，不是跨客户端表面功能对等承诺。

## Codex

- 共享指令：`AGENTS.md`。
- 共享工作流：`.agents/skills/agent-project-os/SKILL.md`。
- 元数据：`.agent-project/adapters/codex.json`。
- Codex 任务或对话不构成核心真源。

## Claude Code

- `CLAUDE.md` 的受管区块导入 `@AGENTS.md`；已有 Claude 专属说明保留在区块外。
- 共享 Skill 映射到 `.claude/skills/agent-project-os/SKILL.md`。
- `SessionStart` 与 `Stop` Hooks 写入最小归一化生命周期事件，不保存提示词、工具参数、终端输出或完整对话。
- 已有 `.claude/settings.json` 键会保留，并在卸载时恢复。

## DeepSeek Harness

- 状态：**preview**。上游明确处于 developer preview，并提示会出现兼容性破坏。
- 固定兼容点：`0.1.0-rc.5`，commit `47f943859bef60e4160492346772ded9b24f765a`。
- 渲染结果是 `.dsh/agent-project-os-bundle` 下的树外 Cordis bundle，并声明 `dsh.bundle.patch` 元数据。
- 使用 `dsh plugin --profile <profile> add ./.dsh/agent-project-os-bundle` 安装到显式 profile，再用 `dsh --profile <profile> --dump-config` 检查。
- Plugin 归一化 session、turn 与 tool 生命周期事件，但不保存工具 payload。

上游破坏兼容时，只修改和复测本 Adapter。不得向核心记录加入 DSH profile、bundle、Cordis 或事件专属字段。

## 安装安全

默认只在项目内渲染：

```sh
agent-project adapter render --adapter all
```

用户级写入必须显式使用 `--user`。已有文件会备份，生成内容记录 hash，重复安装幂等，卸载恢复原内容。若纯生成的受管文件在安装后被修改，CLI 会拒绝覆盖或删除。

```sh
agent-project adapter install --adapter codex --user --dry-run
agent-project adapter install --adapter codex --user
agent-project adapter uninstall --adapter codex --user
agent-project adapter doctor --adapter all
```

官方参考：[Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)、[Codex Skills](https://learn.chatgpt.com/docs/build-skills)、[Claude Code memory](https://code.claude.com/docs/en/memory)、[Claude Code Hooks](https://code.claude.com/docs/en/hooks)、[DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)。
