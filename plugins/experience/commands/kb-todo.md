# /kb-todo

【经验库】记/勾个人待办，可带截止日期；只动本机 todos，不改仓库 Fact。

## 怎么做

1. 解析引擎路径（同 `/kb-note`）。
2. 新增：`python3 <kb> todo add --title "…" [--due YYYY-MM-DD]`
3. 完成：`python3 <kb> todo done <id>`
4. 列表：`python3 <kb> todo list [--overdue]`