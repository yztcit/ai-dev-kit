# claude_plugins 与 experience（0.3）

**分工：** `claude_plugins` 的 `dev` 等插件 = **Playbook（流程）**；`experience` / `kb` = **记忆与复利（本机库 + hooks + `/kb-*`）**。互补，不互相替代。

## 推荐组合

1. 本仓库：`bash plugins/experience/scripts/install_personal.sh`（kb）。  
2. 需要研发流程：marketplace 安装 `dev@claude_plugins`（或其它 Playbook）。  
3. 会话里：Playbook 跑流程；结论用 `/kb-deposit`、`/kb-todo`、`/kb-note` 落盘。

## 命中顺序

SessionStart 先 kb（Fact / 技巧 / 习惯摘要 / 待办展示）→ 你显式调用 `/dev:…` 走 Playbook → 通用做法经 Technique + `/kb-promote` 进候选，**不要**把业务 Fact 写进 claude_plugins 仓。

## 0.3 边界

| 做法 | 支持 |
|---|---|
| 习惯与技巧在开场/命中时注入，叠在 Playbook 之上 | ✅ |
| `/kb-promote` → `inbox-promote/` 供人审 PR | ✅ |
| 根据聊天自动重写 claude_plugins 里的 Skill/Agent | ❌ |
| 从 kb 一键生成私有整套 fork 插件 | ❌ |

`/kb-help claude_plugins`（装 personal 后）与本文同源。

详情：spec §7B · 日常 [`plugins/experience/PERSONAL-USE.md`](../../plugins/experience/PERSONAL-USE.md)。