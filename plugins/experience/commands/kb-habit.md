# /kb-habit

【经验库】记跨项目个人习惯，开场注入摘要；不写进某仓 Fact，不改 claude_plugins。

## 怎么做

1. 解析引擎路径（同 `/kb-note`）。
2. 写入/更新：`python3 <kb> habit upsert --id <id> --title "…" --body-file <路径>` 或 `--body "…"`
3. 列表：`python3 <kb> habit list`