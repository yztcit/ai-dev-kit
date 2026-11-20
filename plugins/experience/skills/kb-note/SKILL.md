---
name: kb-note
description: 插件内剧本（个人版斜杠入口是 /kb-note command，勿再装到 ~/.claude/skills）。当用户说“记一下”“先记下来”“先存一下”“做个草稿”时，把未沉淀内容写入 scratch，经 kb note 落盘与打点。
metadata:
  skill_version: 0.1.2
  owner: experience
  tags:
    - experience
    - scratch
    - capture
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

# 记一下 Skill

## 触发场景

在用户明确要求先留痕、先存草稿、先别展开沉淀时使用，典型表达包括：

- “记一下”
- “先记下来”
- “先存一下”
- “先做个草稿”
- “帮我记个备忘”

只要目标是把当前会话里的原始信息先落到 `scratch/`，就用这个 Skill；不要在这里提前做 Fact / Technique / plans 的最终裁决。

## 目标

把当前会话里值得留存但还没准备好沉淀的内容，写成一份可回看、可继续加工的 scratch 笔记。

### 目录与文件名

落盘由 `kb note` 完成：`scratch/<timestamp>-<slug>.md`（引擎自动加时间戳与 slug 清洗）。

- `slug` 只保留小写字母、数字和短横线，尽量短，能表示主题即可

## 写入原则

- 先保留原话，再做整理，不要把用户原句改写成结论。
- 只记录当前会话里已经出现过的内容，不补编背景。
- 事实、推断、待确认问题要分开写，避免混在一起。
- 这一步不做最终分类，不给 Fact / Technique / plans 盖章。

## 建议内容结构

笔记正文建议至少包含这些段落（整段作为 `--body` 或 `--body-file` 传给 kb）：

```md
---
created_at: 2026-11-19 19:04 +0800
source: session
topic: <slug>
status: scratch
---

## 原始内容
<用户原句或关键片段>

## 当前理解
<你对这段内容的暂时理解>

## 待确认
<还有哪些点会影响后续沉淀>

## 下一步
<如果需要沉淀，下一步该交给 deposit 做什么>
```

## 写盘后必须调用 kb note

组装好正文与 slug 后立刻执行（路径按本机插件位置）：

```bash
KB="$HOME/workspace/AI-dev-kit/plugins/experience/engine/kb"
# 或 EXPERIENCE_PLUGIN_ROOT/engine/kb；或 PERSONAL_INSTALL.json 的 plugin_root

python3 "$KB" note --slug "<slug>" --body-file "<临时正文路径>"
# 或较短正文：
python3 "$KB" note --slug "<slug>" --body "<全文 markdown>"
```

`kb note` 会写入 scratch 并记录 `note` 事件；**不要**再单独执行 `kb event note`。

## 检查清单

- CLI 输出含 `path` 且文件在 `scratch/` 下。
- 文件名带时间戳和主题 slug。
- 用户原句没有被过度改写。
- 没有把内容提前分到 `facts/`、`methods-personal/` 或 `techniques/index.json`。
- 已执行 `kb note`（勿重复 event）。