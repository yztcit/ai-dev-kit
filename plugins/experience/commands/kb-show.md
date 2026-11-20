---
description: 【经验库】只读查看一条 KB 正文/摘要（scratch|technique|habit|todo|facts）；默认截断，--full 全文。
---

# /kb-show

【经验库】按类型 + id 查看内容；不改数据。

## 怎么做

1. 解析引擎路径（同 `/kb-note`）。
2. 先用 `/kb-ls` 或 `kb ls` 拿到 `id`。
3. 执行：`python3 <kb> show <scratch|technique|habit|todo|facts> <id> [--full] [检出目录]`
4. 把输出给用户；过长时提示可用 `--full`。

## 说明

- `todo` 输出 JSON 条目（无独立 md 卡）
- `facts` 的 id 为条目内相对路径（如 `base/CLAUDE.md`），也可用 `kb ls facts` 里的 path
