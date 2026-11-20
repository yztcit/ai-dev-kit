# experience 个人版 0.3 Implementation Plan

> **状态：已归档（2026-11-20）** — 任务已执行完毕。现行用法见 `plugins/experience/PERSONAL-USE.md`；设计见对应 spec（已落地）。勿再按本文开新实现会话。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 按已批准 spec 把个人 AI 助手打到 0.3：`kb` 写契约（note/deposit/todo/habit/off/on/help/status 展示）、分支感知 import、开场生效条、`/kb-*` 命令投影、文档与验收剧本。

**Architecture:** 本机 `~/.local/share/dev-memory` + `plugins/experience/engine/kb` 为唯一写入口；Claude/Cursor 仅投影 `commands/kb-*.md` 与 skills；hooks 读 `state.json` 的 enabled 短路；质量靠 events + doctor + 开场展示。

**Tech Stack:** Python 3 stdlib、unittest、bash hooks、Markdown commands/skills。

**Spec:** `docs/superpowers/specs/2026-11-20-personal-assistant-extreme-design.md`

## Global Constraints

- `PRODUCT_VERSION = "0.3.0"`（`memory_paths.py` 与 `plugin.json` 对齐）。
- 命令前缀一律 `kb-`；菜单注释以 `【经验库】` 开头、口语说明结果。
- 不自动改写 `claude_plugins`；不自动清空检出 `.claude`。
- deposit 校验失败 **整单拒绝**；质量看日志不看提案过目。
- 新域目录：`todos/`、`habits/`、`state.json`；扩展只加顶层目录。
- 测试用 `DEV_MEMORY_ROOT` 临时目录；提交信息用 HEREDOC、不加 Co-Authored-By。

## File map

| 路径 | 职责 |
|---|---|
| `engine/memory_paths.py` | 版本、路径、`ensure_layout` 扩 todos/habits/state |
| `engine/state_ops.py` | on/off、读 enabled |
| `engine/note_ops.py` | `kb note` |
| `engine/deposit_ops.py` | validate + `deposit-apply` |
| `engine/todo_ops.py` | todo add/done/list |
| `engine/habit_ops.py` | habit upsert/list |
| `engine/help_ops.py` | `kb help [topic]` |
| `engine/events.py` | 事件类型 + report 增强 |
| `engine/doctor.py` | DISABLED / 命令投影检查 |
| `engine/kb` | 路由新子命令；import 分支规则；status 增强 |
| `hooks/session_start.sh` | enabled 短路 + 开场展示行 |
| `hooks/prompt_hit.sh` | enabled 短路 |
| `commands/kb-*.md` | `/` 命令权威正文 |
| `skills/*` | 别名改调 kb |
| `scripts/install_personal.py` | 投影 commands → Claude/Cursor |
| `PERSONAL-USE.md` 等文档 | 日常入口与剧本 |
| `engine/tests/test_*.py` | L0 |

---

### Task 1: 布局 / state / 版本

**Files:**
- Modify: `plugins/experience/engine/memory_paths.py`
- Create: `plugins/experience/engine/state_ops.py`
- Modify: `plugins/experience/.claude-plugin/plugin.json`
- Test: `plugins/experience/engine/tests/test_state_and_layout.py`

**Produces:** `PRODUCT_VERSION=="0.3.0"`；`ensure_layout` 创建 `todos/`、`habits/`、`state.json`；`is_enabled()` / `set_enabled(bool)`。

- [x] **Step 1: 写失败测试**

```python
def test_layout_and_toggle():
    # DEV_MEMORY_ROOT 临时目录
    import memory_paths, state_ops
    memory_paths.ensure_layout()
    assert Path(memory_paths.todos_root()).is_dir()
    assert Path(memory_paths.habits_root()).is_dir()
    assert memory_paths.PRODUCT_VERSION == "0.3.0"
    assert state_ops.is_enabled() is True
    state_ops.set_enabled(False)
    assert state_ops.is_enabled() is False
```

- [x] **Step 2: 跑测确认失败** — `python3 -m pytest plugins/experience/engine/tests/test_state_and_layout.py -v`

- [x] **Step 3: 实现** — `todos_root`/`habits_root`/`state_path`；`state.json` 默认 `{"enabled":true,"schema":1}`；`set_enabled` 写盘。

- [x] **Step 4: 跑测通过**

- [x] **Step 5: Commit** — `feat(experience): add 0.3 layout, state toggle, version bump`

---

### Task 2: `kb note` + 事件

**Files:**
- Create: `plugins/experience/engine/note_ops.py`
- Modify: `plugins/experience/engine/kb`（注册 `note`）
- Modify: `plugins/experience/engine/events.py`（若需）
- Test: `plugins/experience/engine/tests/test_note_ops.py`

**Produces:** `kb note --slug X --body-file F` → `scratch/<ts>-<slug>.md` + `event:note`。

- [x] **Step 1: 失败测试** — 调用 `note_ops.write_note(slug="t", body="hi")` 后文件存在且 `summarize` 含 `note:1`。

- [x] **Step 2–4: 实现并测通** — 文件名 `YYYYMMDD-HHMMSS-slug.md`；同 slug 更新最近一份策略按 spec（新建即可满足 0.3 最小）。

- [x] **Step 5: Commit** — `feat(experience): add kb note with event`

---

### Task 3: `deposit-apply` 校验（整单拒绝）

**Files:**
- Create: `plugins/experience/engine/deposit_ops.py`
- Modify: `plugins/experience/engine/kb`
- Test: `plugins/experience/engine/tests/test_deposit_ops.py`

**Produces:**
- `validate_deposit(payload) -> (ok, reasons)`
- `apply_deposit(payload) -> result`；失败写 `deposit_rejected`，磁盘无半写入
- Technique 正文须含 `## 反例`；plans 须 `kind in (exec, reference)`

- [x] **Step 1: 测试无反例拒绝且 methods-personal 无新文件**

```python
def test_reject_missing_counterexample():
    payload = {"facts": [], "techniques": [{"id": "x", "triggers": ["a"], "body_md": "## 情境\n## 做法\n"}], "plans": []}
    ok, reasons = deposit_ops.validate_deposit(payload)
    assert ok is False
    assert "missing_counterexample" in reasons
    r = deposit_ops.apply_deposit(payload)
    assert r["ok"] is False
    assert not list(Path(methods_personal_root()).glob("x.md"))
```

- [x] **Step 2: 测试成功写入 + index + `deposit` 事件 counts**

- [x] **Step 3–4: 实现** — stdin/文件 JSON；整单事务（先校验再写）。

- [x] **Step 5: Commit** — `feat(experience): deposit-apply with all-or-nothing validate`

---

### Task 4: todo + habit

**Files:**
- Create: `plugins/experience/engine/todo_ops.py`, `habit_ops.py`
- Modify: `kb` 路由
- Test: `test_todo_habit_ops.py`

**Produces:**
- `kb todo add|done|list` → `todos/items.jsonl`；事件 `todo_add`/`todo_done`
- `kb habit upsert|list` → `habits/<id>.md` + index；事件 `habit_upsert`
- `list --overdue` 按 `due < today` 且 status!=done

- [x] **Step 1–4: TDD 实现**

- [x] **Step 5: Commit** — `feat(experience): todo and habit stores`

---

### Task 5: off/on、status 展示、doctor、help、report 增强

**Files:**
- Modify: `state_ops.py`, `doctor.py`, `events.py`（report）, `kb`
- Create: `help_ops.py`
- Test: `test_doctor_off_help_report.py`

**Produces:**
- `kb off` / `kb on`；doctor 在 off 时 `status=DISABLED` 且 `ok=True`（或单独字段，文档写明）
- `kb status` 打印 enabled、habits 数、逾期 todo 数（在已有仓状态上增强）
- `kb help [topic]` 读 `commands/kb-<topic>.md` 前几节（topic 映射表）
- report：rejected 计数、todo/habit 计数、bump 候选（hit≥3 且 hypothesis）

- [x] **Step 1–4: TDD**

- [x] **Step 5: Commit** — `feat(experience): off/on, help, report and doctor for 0.3`

---

### Task 6: 分支感知 import + promote 事件 + plans 目录

**Files:**
- Modify: `plugins/experience/engine/kb`（`cmd_import`）
- Test: `test_import_branch_overlay.py`（用临时 git 仓更佳；至少模拟 checkout 分支名与文件树）

**Produces:**（对齐 spec §3）

- 主分支 / 无分支：写入 `base/`（保持现有能力，并 **增加** `plans/` 树，与 agents/rules/skills/tools 并列）
- 功能分支：相对 base 内容相同 → 不写 overlay；不同 → 写 `branches/<branch>/`
- **禁止**功能分支 import 默默改 base
- 成功 append `import` 事件（含 branch、copied 计数）

- [x] **Step 1: 失败测试** — feature 分支改写 `rules/a.md` 后 import，断言文件在 `branches/feature/...` 且 base 旧内容不变。

- [x] **Step 2–4: 实现**（可抽 `_import_tree(checkout, dest_root)` 复用）

- [x] **Step 5: Commit** — `feat(experience): branch-aware kb import with plans`

---

### Task 7: SessionStart 开场条 + hooks 尊重 enabled

**Files:**
- Modify: `hooks/session_start.sh`, `hooks/prompt_hit.sh`
- 可选小模块：`engine/banner.py` 供 hook 调 `python3 -c` / `kb hook-banner`

**Produces:**
- enabled=false → 打印 `[experience] kb OFF · /kb-on` 后退出（或静默）；不 sync、不命中
- enabled=true → 一行：`[experience] kb ON · <key>@<branch> · … · todos逾期:N`；再执行原有 sync/种子逻辑
- 注入 habits 摘要：最多 5 条标题，总长度截断（如 800 字符）

- [x] **Step 1: 手工/脚本测** — `DEV_MEMORY_ROOT=... kb off` 后跑 `bash hooks/session_start.sh </dev/null` 见 OFF。

- [x] **Step 2: 实现 banner**

- [x] **Step 3: Commit** — `feat(experience): session banner and honor kb off`

---

### Task 8: `/kb-*` 命令正文 + install 投影

**Files:**
- Create: `plugins/experience/commands/kb-note.md` …（覆盖 spec 命令表：note, deposit, import, sync, todo, plan, retro, bump, promote, status, report, doctor, help, habit, off, on）
- Modify: `scripts/install_personal.py` — 投影到 `~/.claude/commands/`（若 Claude 支持）与 `~/.cursor/commands/`
- Modify: `doctor.py` — 检查若干关键 `kb-*.md` 是否已投影（缺则为 warn，不使 doctor 变红，除非 `--strict`）

**Produces:** 每条命令 description 用 spec 口语注释；正文只写「调用哪个 `kb` 子命令 + 分流规则要点」。

- [x] **Step 1: 写齐 commands**
- [x] **Step 2: install 复制/软链**
- [x] **Step 3: 跑 install + doctor**
- [x] **Step 4: Commit** — `feat(experience): kb-* slash commands and install projection`

---

### Task 9: Skills 改调 kb；promote 最小版

**Files:**
- Modify: `skills/note/SKILL.md`, `skills/deposit/SKILL.md`
- Create: `skills/habit/SKILL.md`（可选）
- Create: `engine/promote_ops.py` — 复制 technique → `plugins/experience/inbox-promote/<id>.md` + 事件（路径相对插件根）
- Modify: `kb` 注册 `promote-technique` 或扩展现有 promote 文档以免与 fact promote 混淆：用 `kb technique promote <id>`

**Produces:** skill 删除「必须等人看完提案」；改为组 JSON/`kb note`；habit skill 触发语。

- [x] **Step 1–4**
- [x] **Step 5: Commit** — `feat(experience): skills call kb; technique promote inbox`

---

### Task 10: 文档对齐 + L2 剧本

**Files:**
- Rewrite: `plugins/experience/PERSONAL-USE.md`（0.3 命令表、场景、费用、claude_plugins、15min 剧本、off/on）
- Modify: `plugins/experience/README.md`, `EXPERIENCE-COMPOUNDING.md`（0.3 指针）, `health/BACKLOG.md`, `README.md` experience 节
- Create: `docs/adapters/cursor.md`, `docs/adapters/claude_plugins.md`（短）
- Create: `docs/superpowers/README.md`（specs/plans 索引）

**Produces:** 日常只看 PERSONAL-USE；BACKLOG 将 0.3 标进行中/完成项更新。

- [x] **Step 1: 改文档**
- [x] **Step 2: 跑 L0 全测** — `python3 -m pytest plugins/experience/engine/tests -v`
- [x] **Step 3: 跑 L1** — `python3 plugins/experience/engine/kb doctor`
- [x] **Step 4: 按 PERSONAL-USE 剧本列清单（L2 需用户配合时可标待跑）**
- [x] **Step 5: Commit** — `docs(experience): personal 0.3 usage and backlog`

---

## Spec coverage checklist

| Spec 块 | Task |
|---|---|
| 布局 todos/habits/state、版本 | 1 |
| note / deposit 整单拒绝 | 2–3 |
| todo / habit / 更懂用户 | 4, 7, 9 |
| off/on、status、help、report | 5 |
| 分支 import | 6 |
| 开场展示、费用可控注入 | 7 |
| `/kb-*` 命令 | 8 |
| promote、skills、claude_plugins 文档边界 | 9–10 |
| 删本地纪律（文档，无自动清空） | 10 |

## Out of scope this plan

- 系统通知中心提醒  
- 自动生成/改写 claude_plugins  
- `kb gc-local` 自动删除（仅文档承诺 0.3.x）  
- 向量检索、跨设备同步产品  

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-11-20-experience-personal-0.3.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — 每任务新开子代理，任务间审查  
2. **Inline Execution** — 本会话按 executing-plans 连续做，设检查点  

Which approach?
