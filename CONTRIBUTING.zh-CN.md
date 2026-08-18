# 参与 Agent Project OS

[English](CONTRIBUTING.md)

Agent Project OS 接受范围清晰、有证据支撑，并保持核心运行时中立的改动。

## 修改前

1. 阅读 `AGENTS.md`、`docs/METHOD.zh-CN.md`、`docs/PROTOCOL.zh-CN.md` 和相关已接纳决策。
2. 建立一个具有明确验收标准的任务。
3. 客户端差异只能进入 `agent_project_os.adapters`；不得向核心 Schema 添加 Codex、Claude、DeepSeek、模型或供应商专属字段。
4. 测试夹具和报告中不得出现私有路径、业务数据、凭据、完整对话或无关命令输出。

## 开发

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
python -m unittest discover -s tests -p 'test_*.py'
agent-project validate
```

公共行为使用红—绿—重构循环。Schema 变更必须同时增加正例和反例。Adapter 变更必须覆盖 golden file、已有配置保留、幂等、卸载恢复和事件归一化。

## Pull Request

说明结果、协议影响、兼容性影响、确定性验证和人工复核需求。不能仅因 Agent 生成了补丁就宣称完成。英文或中文规范发生变化时，必须在同一改动中更新配对文档。

提交贡献即表示你同意按 Apache-2.0 许可授权该贡献。
