---
description: 【经验库】只读浏览 scratch/technique/habit/todo/facts；统一表格式。facts 默认当前仓，--all 全库。
---

# /kb-ls

【经验库】只读列表；不改数据。

## 怎么做

1. 解析引擎路径（同 `/kb-note`）。
2. 执行：`python3 <kb> ls <scratch|technique|habit|todo|facts> [--json] [--limit N] [--all] [--overdue] [检出目录]`
3. 把表格摘要给用户；需要正文时用 `/kb-show`。

## 说明

- 统一列：`type` · `id` · `title_or_slug` · `meta` · `path`
- `facts` 默认当前检出对应仓；`facts --all` 列出全库所有仓
- `scratch` 默认最近 30 条；其它类型默认全量（可用 `--limit`）
