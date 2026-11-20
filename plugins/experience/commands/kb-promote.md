# /kb-promote

【经验库】把已验证的个人技巧去语境化后导出到可分享候选目录并打点；不自动开 PR、不改 claude_plugins 源码。

## 怎么做

1. 确认技巧已 `used`/`repeated`，正文已去掉业务专名（人工过目）。
2. 解析引擎路径（同 `/kb-note`）。
3. 若引擎已支持：`python3 <kb> technique promote <id>`（写入 `plugins/experience/inbox-promote/` 并记事件）。
4. 若子命令尚不可用：先 `python3 <kb> report` 定位 id，再按插件内 `inbox-promote/` 约定由助手复制候选并提醒用户后续 PR。