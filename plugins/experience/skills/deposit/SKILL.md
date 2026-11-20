---
name: deposit
description: 当用户说“沉淀”“收尾”“存成经验”时，把 scratch + 会话结论拆成 Fact / Technique / plans(kind) 提案；Fact 默认全收，Technique 必须带反例，plans 没有 kind 先问。
metadata:
  skill_version: 0.1.0
  owner: experience
  tags:
    - experience
    - deposit
    - fact
    - technique
supported_runtimes: []
required_capabilities:
  filesystem_read: true
  filesystem_write: true
  tool_use: false
  network: false
  binary_outputs: false
io_contract:
  output_kind: text
---

# 沉淀 Skill

## 触发场景

在用户明确要求“沉淀”“收尾”“整理成经验”“存进知识库”时使用。

这个 Skill 负责把 scratch 和当前会话结论拆成可写入的候选项，并在用户确认后落盘。

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
2. 先产出一份“拆分提案”，把候选项分成 Fact / Technique / plans(kind)。
3. 对于会影响写入位置或类型的模糊项，先向用户确认。
4. 用户确认后再写盘，不要先写后补问。
5. 写入后同步更新索引和引用关系，避免内容和 index 漂移。

## 写入落点

### Fact

- 写入 `facts/` 下对应身份路径。
- 按现有布局进入 `base/` 或 `branches/<分支>/`，不要自行发明新层级。

### Technique

- 写入 `MEMORY_ROOT/methods-personal/<slug>.md`。
- 个人 Technique 卡的内容要便于后续晋升为插件包。
- 如果当前仓是 team-tracked，只做加性写入，不要用“覆盖 CLAUDE.md”之类的表述。

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

写入或更新卡片时，必须同步检查 `MEMORY_ROOT/methods-personal/index.json`：

- `path` 指向这张卡的实际路径。
- `triggers` 与卡片头保持一致。
- `strength` 与卡片头保持一致。
- 如果卡片触发词、强度或路径变了，索引要同一轮更新，不能留旧值。

公开插件包内的 `plugins/experience/techniques/index.json` 只保留可分享技巧；个人 Technique 不要写到这里。

## `methods-personal/index.json` 更新要求

`index.json` 是命中入口，格式保持为条目数组，每个条目至少包含：

- `path`
- `triggers`
- `strength`

更新时遵守这些规则：

- 新卡上线后再把条目写入索引。
- 改卡时先改卡，再同步改索引。
- 删除卡时同步删索引条目。
- `contradicted` 不自动灌进启动命中清单。

## 写盘后必须打点（个人版反馈）

用户确认并完成写入后立刻执行：

```bash
python3 "$HOME/workspace/AI-dev-kit/plugins/experience/engine/kb" event deposit \
  --fact_count "<N>" \
  --technique_count "<N>" \
  --plans_count "<N>"
```

可选再附 `--json '{"paths":["..."]}'`。没有这条事件，`kb report` 无法统计沉淀。

## 交付前检查

- Fact、Technique、plans 已明确分开。
- plans 里没有 `kind` 的条目都已经先问。
- Technique 卡都有反例。
- `methods-personal` 与 `methods-personal/index.json` 没有漂移。
- team-tracked 场景没有出现“覆盖 CLAUDE.md”这种不必要的表述。
- 已执行 `kb event deposit`。

