---
description: 【经验库】用 KB 刷新当前检出的 `.claude` / `CLAUDE.md` 投影；不写入 KB base。
---

# /kb-sync

【经验库】用 KB 刷新当前检出的 `.claude` / `CLAUDE.md` 投影；不写入 KB base。

## 怎么做

1. 解析引擎路径（同 `/kb-note`）。
2. 执行：`python3 <kb> sync [检出目录]`（默认当前目录）。
3. 手工改过投影会被检测并覆盖；唯一可写处仍是 KB。
