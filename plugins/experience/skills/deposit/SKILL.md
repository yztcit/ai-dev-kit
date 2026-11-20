---
name: kb-deposit
description: 当用户说“沉淀”“收尾”“存成经验”或使用 /kb-deposit 时，把 scratch + 会话结论拆成 Fact / Technique / plans(kind) JSON，经 kb deposit-apply 整单写入。
metadata:
  skill_version: 0.1.1
  owner: experience
  tags:
    - experience
    - deposit
    - fact
    - technique
supported_runtimes: []
required_capabilities:
  filesystem_read: true
  filesystem_write: false
  tool_use: true
  network: false
  binary_outputs: false
io_contract:
  output_kind: text
---

# 沉淀 Skill

## 触发场景

在用户明确要求“沉淀”“收尾”“整理成经验”“存进知识库”时使用。

把 scratch 和当前会话结论拆成可写入项，组装 JSON 后交给 `kb deposit-apply` 校验并落盘。

## 目标

把原始记录拆成三类：

- `Fact`：本仓成立的事实，默认尽量全收，只剔错、剔重复。
- `Technique`：可去语境复用的方法，必须提供反例。
- `plans`：执行计划或资料计划，必须先标明 `kind`，`kind` 不明就先问。

## 拆分规则

### Fact

- 默认全收。
- 只有明显错误、冲突、重复时才删。
- 不要把 Fact 改写成 Technique，也不要把 Technique 反向降成 Fact，除非它确实去语境失败。

### Technique

- 只有当它能脱离当前会话、在别的场景复用时，才提成 Technique。
- 每张 Technique 卡都必须有反例或失败边界。
- 没有反例时，最多先当作 `hypothesis` 草案，不要直接升到 `used` / `repeated`。
- 不要在缺少反例时硬写进公开可分享层。

### plans

- 任何计划条目都先判断 `kind`。
- `kind` 不明时先问用户，不要默认为 `exec` 或 `reference`。
- 已知 `kind` 后，再决定是留在 plans、迁到 Fact，还是做后续归档。

## 写入流程

1. 读取最新 scratch 和本会话结论。
2. 组装 **deposit 提案 JSON**（`facts` / `techniques` / `plans` 数组，字段与引擎校验一致）。
3. 用户口头否决某项时，**从 JSON 中删掉该条**再 apply，不必为「等用户看完整份提案」而阻塞。
4. 执行 apply；校验失败（整单拒绝）时按 CLI 原因改 JSON 后重跑即可。
5. 成功以 CLI 与 `deposit` 事件为准；索引同步由引擎处理。

### 引擎调用

```bash
KB="$HOME/workspace/AI-dev-kit/plugins/experience/engine/kb"

python3 "$KB" deposit-apply --file "<提案.json>"
# 或管道：
cat "<提案.json>" | python3 "$KB" deposit-apply
```

**不要**再手写落盘到 `facts/` / `methods-personal/` 而跳过 deposit-apply；**不要**单独 `kb event deposit`（apply 成功会打点）。

## JSON 与落点（引擎侧）

### Fact

- 由 `facts` 条目指定身份路径；按现有布局进入 `base/` 或 `branches/<分支>/`，不要自行发明新层级。

### Technique

- 写入 `MEMORY_ROOT/methods-personal/<slug>.md` 并更新 `methods-personal/index.json`。
- 个人 Technique 卡的内容要便于后续晋升为插件包。
- team-tracked 场景只做加性写入。

## `methods-personal` 卡片格式

建议使用统一的卡片头，并和 `MEMORY_ROOT/methods-personal/index.json` 保持一致：

```md
---
id: explore-before-edit
kind: technique
triggers: ["动手改代码前", "不确定现状"]
scope: personal
verified_at: 2026-11-19
strength: hypothesis
---

## 情境
## 做法
## 反例
## 来源
```

公开插件包内的 `plugins/experience/techniques/index.json` 只保留可分享技巧；个人 Technique 不要写到这里。

## 交付前检查

- Fact、Technique、plans 在 JSON 中已明确分开。
- plans 里没有 `kind` 的条目都已经先问或已剔除。
- Technique 卡都有反例。
- 用户否决项未出现在最终 JSON。
- 已执行 `kb deposit-apply` 且成功。