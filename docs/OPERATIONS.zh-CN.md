# 运维、迁移与恢复

[English](OPERATIONS.md)

## 可恢复的旧 Portfolio 迁移

在既有 `portfolio.json` 旁初始化组织，然后先预览再执行：

```sh
agent-project migrate portfolio-v1 --dry-run --json
agent-project migrate portfolio-v1 --json
```

命令要求 `project-registry.json` 为空；它会复制旧项目关系，补上默认 weekly 监督策略和 `P2` 优先级，再把旧文件移动到 `.agent-project/migrations/portfolio-v1.archived.json`。校验会拒绝新注册表与旧 Portfolio 同时双写。若要回滚，必须先获得明确批准、移除新注册表，再把归档文件移回。

## 可重建投影

```sh
agent-project index rebuild --json
agent-project dashboard build --as-of 2026-08-18T01:00:00Z --json
```

`.agent-project/index.sqlite3`、`index/dashboard.json` 与 `index/dashboard.html` 都可删除。只读大盘展示优先级、Owner、PM、最新报告接纳、阻塞、下一验收、到期监管、CEO 例外和 Agent 版本。

## 私有影子对账

`agent-project shadow compare --snapshot /path/to/local-snapshot.json --json` 只读取用户拥有的 JSON 快照并输出差异，不导入、不改写、不持久化外部数据。私有路径映射、业务名称和快照必须留在公共仓库之外。只有连续两个完整监督周期没有关键分歧，才可以提出单真源切换。

## 恢复边界

- Git 记录是恢复来源；SQLite 和大盘文件可以删除。
- Cadence 重试有上限，终态 run 不能被静默重开。
- Agent 回滚要求旧版本资产 digest 仍然有效。
- `portfolio.json` 被归档而不是抹除。
- tag、GitHub Release、包发布、私有项目切换和试点扩张都需要单独人工批准。
