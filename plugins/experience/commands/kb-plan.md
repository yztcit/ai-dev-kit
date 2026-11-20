---
description: 【经验库】把目标拆成可执行待办写入清单；长文设计仍走 `/kb-deposit` 的 plans，不自动改代码。
---

# /kb-plan

【经验库】把目标拆成可执行待办写入清单；长文设计仍走 `/kb-deposit` 的 plans，不自动改代码。

## 怎么做

1. 与用户敲定步骤后，对每条可执行项调用：`python3 <kb> todo add --title "…" [--due 日期]`（引擎路径同 `/kb-note`）。
2. 需要持久设计文档时，用 `/kb-deposit` 写 `plans`（带 `kind`），勿用 todo 代替计划正文。
3. 以 `kb todo list` 输出为清单真相。
