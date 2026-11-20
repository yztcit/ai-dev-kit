---
description: 【经验库】把会话拆成 Fact / Technique / 仓内 plans，校验后整单写入 KB；不改检出里的 `.claude` 源稿。别名：沉淀 / 收尾 / 存成经验。
---

# /kb-deposit

【经验库】把会话拆成 Fact / Technique / 仓内 plans，校验后整单写入 KB；不改检出里的 `.claude` 源稿。

用户说「沉淀」「收尾」「存成经验」且未用斜杠时，按本命令执行。

## 怎么做

1. 先把提案整理成 JSON（facts / techniques / plans），与用户确认；细节可对照 `skills/kb-deposit/SKILL.md`。
2. 解析引擎路径（同 `/kb-note`）。
3. 执行：`python3 <kb> deposit-apply --file <提案.json>`。
4. 校验失败时修正 JSON 再跑；成功以 CLI 与 events 为准。
