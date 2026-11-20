# /kb-retro

【经验库】按近几日事件复盘，建议 bump / todo / promote；只读报告与索引，不自动改库。

## 怎么做

1. 解析引擎路径（同 `/kb-note`）。
2. 执行：`python3 <kb> report [--days 7] [--json]`。
3. 据报告向用户建议：逾期待办 → `kb todo`；命中多的技巧 → `kb technique bump`；可分享技巧 → `/kb-promote`。
4. 建议须用户确认后再调用对应子命令。