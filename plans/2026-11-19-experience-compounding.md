# 经验复利 V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地经验复利 V1：本机 Fact + 可分享 Technique 运行时，退役 personal-kb 公开业务树，在 aivoice 上跑通「记一下 → 沉淀 → 下会话命中」。

**Architecture:** `AI-dev-kit/plugins/experience` 提供 `kb` 引擎（读 `~/.local/share/dev-memory`）、SessionStart hook、沉淀 skill、Technique 索引命中。业务 Fact 只存本机；公开包零业务。团队已跟踪文件不覆盖，改用加性注入。

**Tech Stack:** Python 3 stdlib（引擎）、Claude Code / Cursor plugin（hooks + skills）、本机目录约定。

**Spec:** [`../EXPERIENCE-COMPOUNDING.md`](../EXPERIENCE-COMPOUNDING.md)

## Global Constraints

- 公开 git / 插件包内 **零业务 Fact**（无 `git.100tal.com` 等业务树）。
- `MEMORY_ROOT` 默认 `~/.local/share/dev-memory`；可用环境变量覆盖。
- 已 `git ls-files` 跟踪的路径 **禁止投影覆盖**。
- Technique 默认 `strength: hypothesis`；无反例不得升 `used+`；`hypothesis` 不得进可分享包。
- 不一次性清理所有项目；V1 只迁 aivoice。
- 提交信息用英文或中文短句说明 why；不 force-push；不改 git config。

## File map（将创建/修改）

| 路径 | 职责 |
|---|---|
| `plugins/experience/.claude-plugin/plugin.json` | 插件元数据 |
| `plugins/experience/engine/kb` | 从 personal-kb 迁入并改根路径的 CLI |
| `plugins/experience/engine/memory_paths.py` | MEMORY_ROOT / facts / methods 路径常量 |
| `plugins/experience/hooks/hooks.json` | SessionStart：sync/注入/未接入提示 |
| `plugins/experience/skills/deposit/SKILL.md` | 沉淀（边标说明 + 收尾拆分） |
| `plugins/experience/skills/note/SKILL.md` | 「记一下」→ scratch |
| `plugins/experience/techniques/` + `index.json` | 种子卡与索引 |
| `.claude-plugin/marketplace.json` | 登记 experience 插件 |
| `~/.local/share/dev-memory/**` | 本机运行时数据（不进 git） |
| `personal-kb` 公开仓 | 去业务 + 重定向 README |

---

### Task 1: Scaffold `experience` 插件与 MEMORY_ROOT

**Files:**
- Create: `plugins/experience/.claude-plugin/plugin.json`
- Create: `plugins/experience/engine/memory_paths.py`
- Create: `plugins/experience/README.md`
- Modify: `.claude-plugin/marketplace.json`
- Test: shell 创建目录 + python import

**Interfaces:**
- Produces: `memory_paths.MEMORY_ROOT`, `facts_root()`, `methods_personal_root()`, `ensure_layout()`

- [ ] **Step 1: 写 `memory_paths.py`**

```python
# plugins/experience/engine/memory_paths.py
import os

HOME = os.path.expanduser("~")
MEMORY_ROOT = os.path.realpath(
    os.environ.get("DEV_MEMORY_ROOT") or os.path.join(HOME, ".local", "share", "dev-memory")
)

def facts_root():
    return os.path.join(MEMORY_ROOT, "facts")

def methods_personal_root():
    return os.path.join(MEMORY_ROOT, "methods-personal")

def scratch_root():
    return os.path.join(MEMORY_ROOT, "scratch")

def inbox_root():
    return os.path.join(MEMORY_ROOT, "inbox")

def index_path():
    return os.path.join(MEMORY_ROOT, "index.json")

def ensure_layout():
    for p in (
        facts_root(),
        methods_personal_root(),
        scratch_root(),
        os.path.join(inbox_root(), "facts"),
        os.path.join(inbox_root(), "methods"),
    ):
        os.makedirs(p, exist_ok=True)
    if not os.path.isfile(index_path()):
        with open(index_path(), "w", encoding="utf-8") as f:
            f.write('{"schema":1,"entries":{},"never_remind":[]}\n')
    return MEMORY_ROOT
```

- [ ] **Step 2: 写 plugin.json 与登记 marketplace**

`plugin.json`:
```json
{
  "name": "experience",
  "description": "经验复利：本机 Fact 投影/加性注入、沉淀拆分、Technique 命中。无业务内容。",
  "version": "0.1.0"
}
```

在 `marketplace.json` 的 `plugins` 数组追加：
```json
{
  "name": "experience",
  "source": "./plugins/experience",
  "description": "经验复利运行时：Fact / Technique / 沉淀 skill（本机数据，包内无业务）",
  "category": "productivity"
}
```

- [ ] **Step 3: README 写清安装与 MEMORY_ROOT（无业务路径示例用占位符）**

- [ ] **Step 4: 验证**

```bash
python3 -c "import sys; sys.path.insert(0,'plugins/experience/engine'); from memory_paths import ensure_layout; print(ensure_layout())"
ls ~/.local/share/dev-memory
```

Expected: 打印 MEMORY_ROOT；目录含 `facts` `methods-personal` `scratch` `inbox` `index.json`。

- [ ] **Step 5: Commit（在 AI-dev-kit 仓）**

```bash
git add plugins/experience .claude-plugin/marketplace.json
git commit -m "$(cat <<'EOF'
feat(experience): scaffold plugin and memory root helpers

EOF
)"
```

---

### Task 2: 迁入 `kb` 引擎并改读本机 facts

**Files:**
- Create: `plugins/experience/engine/kb`（从 `~/workspace/personal-kb/kb` 复制后改）
- Create: `plugins/experience/engine/tests/test_normalize_and_overlay.py`
- Modify: `kb` 内 `KB_ROOT` → 默认 `facts_root()` 的父布局：条目在 `facts/<identity>/`，不再用 `repos/` + 顶层 `index.json` 双轨；统一读 `MEMORY_ROOT/index.json`

**Interfaces:**
- Consumes: `memory_paths.ensure_layout`, `facts_root`, `index_path`
- Produces: CLI `hook|sync|status|import|promote|check|verify`；`detect_overlay(checkout) -> "personal"|"team-tracked"`；`sync` 跳过 git 跟踪文件

- [ ] **Step 1: 复制并改根路径**

```bash
cp ~/workspace/personal-kb/kb plugins/experience/engine/kb
chmod +x plugins/experience/engine/kb
```

将文件头 `KB_ROOT` 逻辑改为：
- 数据根 = `DEV_MEMORY_ROOT` / 默认 `~/.local/share/dev-memory`
- 条目目录 = `facts/<identity>/`（内含 `base/`、`branches/`、`kb.yml`）
- `index.json` = MEMORY_ROOT 下那份
- USAGE 文案去掉 personal-kb 产品名，改为 experience kb

- [ ] **Step 2: 实现 `detect_overlay(checkout)`**

规则：若 `CLAUDE.md` 或 `.claude/settings.json` 或 `.claude/agents` 下任一文件被 `git ls-files` 跟踪 → `team-tracked`，否则 `personal`。结果写入该条目 `kb.yml` 的 `overlay:` 字段（import/sync 时）。

- [ ] **Step 3: 改 `sync`：team-tracked / 跟踪文件**

对每个将写入检出的相对路径：
1. 若 `git -C checkout ls-files --error-unmatch <path>` 成功 → **跳过写入**，记入 status。
2. `overlay: team-tracked` 时：不写根 `CLAUDE.md`/`AGENTS.md`；将个人索引投影到 `.claude/personal/`（若目录存在或可创建）且确保不跟踪；同时 hook 侧加性注入（Task 4）。

- [ ] **Step 4: 单测 normalize + overlay 探测（tmpdir + 假 git 或 mock）**

```python
# 最小：normalize_remote 单测（无 git）
def test_normalize_https_and_ssh_same():
    from importlib.machinery import SourceFileLoader
    kb = SourceFileLoader("kb", "plugins/experience/engine/kb").load_module()
    a = kb.normalize_remote("https://git.example.com/group/repo.git")
    b = kb.normalize_remote("git@git.example.com:group/repo.git")
    assert a == b == "git.example.com/group/repo"
```

Run: `python3 plugins/experience/engine/tests/test_normalize_and_overlay.py`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/experience/engine
git commit -m "$(cat <<'EOF'
feat(experience): port kb engine to local dev-memory facts

EOF
)"
```

---

### Task 3: 迁 aivoice Fact 到本机 + 切换本机 hook

**Files:**
- Local only: `~/.local/share/dev-memory/facts/git.100tal.com/znxx_pad/znxx_pad_aivoice/**`
- Modify: 用户 Claude/Cursor SessionStart 指向新 `kb hook`（本机 settings，不进业务仓）
- Modify: `personal-kb/skills/shared-config` 或 AI-dev-kit 内 skill 文案改指向

**Interfaces:**
- Consumes: Task 2 `kb import` / 目录搬迁
- Produces: aivoice 条目可 `kb sync`；旧 `KB_ROOT/repos/...` 可保留作备份直至 Task 5

- [ ] **Step 1: 搬迁**

```bash
python3 -c "import sys; sys.path.insert(0,'/Users/tal/workspace/AI-dev-kit/plugins/experience/engine'); from memory_paths import ensure_layout; ensure_layout()"
mkdir -p ~/.local/share/dev-memory/facts/git.100tal.com/znxx_pad
rsync -a ~/workspace/personal-kb/repos/git.100tal.com/znxx_pad/znxx_pad_aivoice/ \
  ~/.local/share/dev-memory/facts/git.100tal.com/znxx_pad/znxx_pad_aivoice/
# 更新 index.json entries 指向上述相对路径 facts/...
```

- [ ] **Step 2: 在 aivoice 检出跑**

```bash
python3 /Users/tal/workspace/AI-dev-kit/plugins/experience/engine/kb status <aivoice检出>
python3 .../kb sync <aivoice检出>
```

Expected: 身份正确；personal 模式可投影；哈希一致（若有第二检出则对打）。

- [ ] **Step 3: 本机 SessionStart 改为调用新 kb hook**（改 `~/.claude/settings.json` 或等价；**不要**把本机绝对路径提交进 AI-dev-kit 业务示例以外的强制配置）

- [ ] **Step 4: Commit 仅文档/skill 指向变更（若有进仓文件）**；本机 data 不 commit。

---

### Task 4: SessionStart 加性注入 + 未接入提示 + Technique 命中骨架

**Files:**
- Create: `plugins/experience/hooks/hooks.json`
- Create: `plugins/experience/hooks/session_start.sh`
- Create: `plugins/experience/engine/hit_techniques.py`
- Create: `plugins/experience/techniques/index.json`（先空 entries）

**Interfaces:**
- Produces: hook stdout 追加 `[personal-fact]` 摘要或路径列表；未接入提示；`hit_techniques.match(triggers, text) -> list`

- [ ] **Step 1: `hit_techniques.py`**

输入：用户消息或空（开场）、`index.json`。  
输出：按 strength 过滤后的路径列表（contradicted 排除自动灌）。  
V1 匹配：任意 trigger 子串命中（大小写不敏感）。

- [ ] **Step 2: `session_start.sh`**

1. `ensure_layout` + `kb hook`（sync 语义）。  
2. 若未登记 → 打印接入提示三选一说明。  
3. 若 `overlay=team-tracked` 且存在 `PERSONAL.md` → 打印加性注入提示（路径）。  
4. 调用 `hit_techniques`（开场可只加载 `repeated`/`used` 高优先级，或打印短清单）。

- [ ] **Step 3: `hooks.json` 注册 SessionStart 指向该脚本（参照 `plugins/conventions/hooks`）**

- [ ] **Step 4: 干跑脚本**（在 aivoice 目录）

Expected: 无 traceback；已接入仓不提示 import。

- [ ] **Step 5: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat(experience): session start inject and technique hit stub

EOF
)"
```

---

### Task 5: 公开 personal-kb 去业务并退役叙事

**Files:**
- Modify: `~/workspace/personal-kb/` — 删除跟踪的 `repos/**` 业务文件；改 `.gitignore` 为忽略 `repos/`；README 改为重定向至 AI-dev-kit experience
- Optional: 新裸仓或 `git filter-repo` 清历史（选更快达到「新鲜 clone 无业务」者）

**验收:**

```bash
# 在临时目录
git clone git@github.com:yztcit/personal-kb.git /tmp/pkb-check
find /tmp/pkb-check -iname '*aivoice*' -o -path '*znxx_pad*' | head
```

Expected: 无业务树；README 指向 experience。

- [ ] **Step 1: 工作树删除业务文件并改 ignore/README**
- [ ] **Step 2: 推送（需用户明确同意再 push）**
- [ ] **Step 3: 若历史仍含业务 → filter-repo 或新仓；再次 clone 验收**

---

### Task 6: 沉淀 skill（note + deposit）

**Files:**
- Create: `plugins/experience/skills/note/SKILL.md`
- Create: `plugins/experience/skills/deposit/SKILL.md`

**Interfaces:**
- note：写入 `scratch/<timestamp>-<slug>.md`
- deposit：读 scratch + 会话结论 → 提案拆分 Fact/Technique/plans(kind) → 用户确认后写入 `facts/` 或 `methods-personal/` 并更新 `techniques/index.json`（personal 卡可先写在 MEMORY_ROOT/methods-personal 并由 index 扫描）

- [ ] **Step 1: 写 note skill**（description 含「记一下」「先记下来」）
- [ ] **Step 2: 写 deposit skill**（强制拆分；Fact 默认全收；Technique 需反例；plans 无 kind 先问；team-tracked 不提「覆盖 CLAUDE.md」）
- [ ] **Step 3: 手工演练一条假 scratch → 写入 methods-personal 测试卡 → index 能列到**
- [ ] **Step 4: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat(experience): add note and deposit skills

EOF
)"
```

---

### Task 7: 种子 Technique 3～5 张 + 实机验收清单

**Files:**
- Create: `plugins/experience/techniques/*.md`（仅 universal、无专名）
- Modify: `plugins/experience/techniques/index.json`

种子主题建议（去语境）：探索后再改、确认≠真理、团队文档加性注入、plans 先分 exec/reference、沉淀强制拆分 Fact/Method。

- [ ] **Step 1: 撰写卡片（含反例、triggers、strength: used 或 hypothesis）**
- [ ] **Step 2: 更新 index.json**
- [ ] **Step 3: 按 spec §9 跑验收**

| 检查 | 命令/动作 | 期望 |
|---|---|---|
| 投影一致 | 两 aivoice 检出 `kb sync` + 哈希 | 一致（personal） |
| 公开包无业务 | `find plugins/experience -type f \| xargs grep -l znxx_pad` | 无命中 |
| 命中 | 新会话提触发词 | ≥ 提示或注入 |
| 沉淀 | note → deposit | 一次确认后可命中 |
| 安装路径 | README 仅 marketplace/plugin | 无「clone 三仓」 |

- [ ] **Step 4: Commit 种子卡**

---

### Task 8: 文档收尾

**Files:**
- Modify: `DESIGN.md` §八（已有指针则核对）
- Modify: `health/BACKLOG.md` #4 标 V1 实施中/完成项
- Modify: `EXPERIENCE-COMPOUNDING.md` 若有与实现不一致的路径名则改齐
- Modify: `README.md`（AI-dev-kit）增加 experience 一节
- Modify: personal-kb README 重定向（若 Task 5 未完成则本任务完成）

- [ ] **Step 1: 更新文档与 BACKLOG**
- [ ] **Step 2: Commit**

```bash
git commit -m "$(cat <<'EOF'
docs: experience compounding V1 pointers and backlog

EOF
)"
```

---

## Spec coverage（self-review）

| Spec 节 | Task |
|---|---|
| 本机 Fact + 分支模型 | 2, 3 |
| 捕获/拆分/强度 | 6, 7 |
| 命中分档 | 4, 7 |
| plans kind | 6（skill 规则）；巡检可后置 |
| personal-kb 退役 / 零业务 | 5 |
| 分发单插件 | 1, marketplace |
| 扩仓提示 / team-tracked 加性 | 2, 4, 6 |
| 增量迁仓 | 3（仅 aivoice） |
| V1 指标 | 7 |

**故意后置（不阻塞 V1 闭环）：** plans 目录自动巡检脚本、强度自动升降的完整埋点、对外发布流水线。在 deposit skill 中用规则约束即可。

---

## Execution Handoff

Plan complete and saved to `AI-dev-kit/plans/2026-11-19-experience-compounding.md`.

**Two execution options:**

1. **Subagent-Driven（推荐）** — 每任务新 subagent，任务间审查  
2. **Inline Execution** — 本会话按 executing-plans 连续做，设检查点  

你要哪一种？
