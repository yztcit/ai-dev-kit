---
name: kb-habit
description: 插件内剧本（斜杠入口是 /kb-habit command）。当用户说「记住我习惯」「个人习惯」「我的偏好是」时，调用 kb habit upsert 写入习惯库。
metadata:
  skill_version: 0.1.1
  owner: experience
  tags:
    - experience
    - habit
    - personal
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

# 个人习惯 Skill

## 触发场景

用户要把**跨项目、跨仓库**都适用的个人习惯记下来，典型表达包括：

- 「记住我习惯……」
- 「个人习惯是……」
- 「以后都按这个偏好来」
- 「我的默认语言/提交风格/沟通方式是……」

不要把某仓专属配置写进习惯库；仓内 Fact 或 plans 用 deposit，临时草稿用 note。

## 目标

把习惯落成 `habits/<id>.md` 并更新 `habits/index.json`，供 Session 摘要注入。

## 怎么做

1. 从用户表述抽出稳定的 `id`（小写、数字、短横线）、简短 `title`、正文 `body`。
2. 解析引擎路径（同 note skill）：

```bash
KB="$HOME/workspace/AI-dev-kit/plugins/experience/engine/kb"
# 或 EXPERIENCE_PLUGIN_ROOT/engine/kb；或 PERSONAL_INSTALL.json 的 plugin_root
```

3. 执行 upsert（二选一）：

```bash
python3 "$KB" habit upsert --id "<id>" --title "<标题>" --body "<正文>"
# 或正文较长时：
python3 "$KB" habit upsert --id "<id>" --title "<标题>" --body-file "<路径>"
```

4. 以 CLI 输出为准；`habit upsert` 会打点 `habit_upsert` 事件，不要重复 `kb event`。

## 检查清单

- `id` 符合 slug 规则（勿空格、勿大写混用）。
- 正文是可复用的个人偏好，不是单次任务或某项目路径清单。
- 已执行 `kb habit upsert`。