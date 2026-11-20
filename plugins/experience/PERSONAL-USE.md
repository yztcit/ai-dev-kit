# 个人版日常用法（完整产品）

**产品版本：0.3.0**（与 `memory_paths.PRODUCT_VERSION` / `plugin.json` 一致）

日常只看本页。设计定稿见 [`docs/superpowers/specs/2026-11-20-personal-assistant-extreme-design.md`](../../docs/superpowers/specs/2026-11-20-personal-assistant-extreme-design.md)。

目标：本机 **记得住、用得上、看得见、关得掉**；质量看 `events.jsonl`、开场条、`kb report`，不靠「提案过目」。

---

## 一次安装

```bash
bash ~/workspace/AI-dev-kit/plugins/experience/scripts/install_personal.sh
python3 ~/workspace/AI-dev-kit/plugins/experience/engine/kb doctor
```

install 会：建 `~/.local/share/dev-memory`（含 `todos/`、`habits/`、`state.json`）、拷种子技巧、软链 `note`/`deposit` skills、注册 Claude hooks、把 `commands/kb-*.md` **投影**到 `~/.claude/commands/` 与 `~/.cursor/commands/`。

换机器或挪了 `AI-dev-kit` 目录后重跑 install。`doctor` 全绿即可（`kb off` 时为 **DISABLED**，仍算通过）。

---

## `/kb-*` 命令表

在 Claude Code / Cursor 输入 `/kb-…`（正文来自本插件 `commands/kb-*.md`，与 CLI 同源）。

| 命令 | 你会得到什么 |
|---|---|
| `/kb-note` | 草稿进 `scratch/`，打点 `note` |
| `/kb-deposit` | 拆 Fact / Technique / plans，整单校验后入库 |
| `/kb-import` | 按当前 git 分支收 `.claude` → `facts/…/base` 或 `branches/<分支>` |
| `/kb-sync` | 按当前分支把 KB 投影回检出 `.claude` |
| `/kb-todo` | 个人待办 `todos/items.jsonl`（可 due） |
| `/kb-plan` | 目标拆成待办（长文设计仍走 deposit） |
| `/kb-habit` | 跨仓习惯卡 `habits/`，开场摘要注入 |
| `/kb-retro` | 按日志提议 bump / todo / 习惯（写入需你确认） |
| `/kb-bump` | 技巧升档或标否定 |
| `/kb-promote` | 已验证技巧 → `inbox-promote/` 候选 |
| `/kb-status` | ON/OFF、仓身份、分支、overlay、逾期 todo |
| `/kb-report` | 近 N 天事件汇总 |
| `/kb-doctor` | 安装与健康（同 CLI） |
| `/kb-help` | 查子主题，如 `/kb-help deposit` |
| `/kb-off` / `/kb-on` | 一键关/开 hooks 注入（**不删**本机数据） |

自然语言别名：`记一下` → note skill；`沉淀` → deposit skill（内部改调 `kb`）。

等价 CLI（脚本/自动化）：

```bash
python3 .../engine/kb note --slug t --body "…"
python3 .../engine/kb deposit-apply --file payload.json
python3 .../engine/kb todo add "标题" --due 2026-11-25
python3 .../engine/kb off
python3 .../engine/kb help import
```

---

## 怎么知道 kb 在生效

**开场条（主信号）**：SessionStart 且 `kb on` 时注入一行，例如：

```text
[experience] kb ON · myrepo@feature-x · … · todos逾期:1
```

- 本仓未 import：`… 本仓未 import · 仅技巧/待办可用 · /kb-import 可接入`
- `kb off`：`[experience] kb OFF · 输入 /kb-on 恢复`（hooks 仍在，靠开关短路）

**主动查**：`/kb-status`、`/kb-doctor`、`/kb-report`。

**间接**：话术命中技巧卡；`logs/events.jsonl` 增长。

---

## 费用与上下文占用

| 项 | 说明 |
|---|---|
| kb 本身 | 本机文件 + CLI，**无额外 kb 云费**；仍按 Claude/Cursor 模型计费 |
| 多出来的 token | 开场行、技巧命中全文、Fact 投影被读入上下文 |
| 觉得贵或干扰 | `/kb-off` 立即无注入；或精简高 hit 技巧卡 |

详情：`/kb-help` 或 spec §7A。

---

## 与 `claude_plugins`（Playbook）

- **experience / kb**：记忆、待办、复利、投影。
- **claude_plugins `dev`**：dev-flow、审查、实施等**流程**。

推荐：先 `install_personal`（kb），需要流程再 marketplace 装 `dev`。流程里产出的结论用 `/kb-deposit` / `/kb-todo` 落盘。

**0.3 不做**：自动改写或生成 `claude_plugins` 包；定制靠 **习惯/技巧注入** 与 `/kb-promote` 候选，人工 PR 进公共层。

适配说明：[`docs/adapters/claude_plugins.md`](../../docs/adapters/claude_plugins.md)。

---

## 15 分钟验收剧本（L2）

在已接入的仓里自测（可勾选）：

1. `kb doctor` → OK  
2. `kb status` → enabled、仓/分支信息合理  
3. `/kb-note` 或 `kb note` → `scratch/` 有文件，report 含 `note`  
4. `/kb-deposit`（≥2 条，Technique 含 `## 反例`）→ 成功；无反例应整单拒绝  
5. `kb todo add` + `--due` 昨天 → status/report 见逾期  
6. `kb report --days 7` → 有计数  
7. `kb off` → 再触发 SessionStart 见 OFF、无 sync/命中  
8. `kb on` → doctor → 开场恢复 ON  

分支仓可选：`feature` 上改 `.claude` 后 `kb import`，确认进 `branches/<名>` 且 base 不变。

---

## 反馈数据

```text
~/.local/share/dev-memory/logs/events.jsonl
```

```bash
python3 ~/workspace/AI-dev-kit/plugins/experience/engine/kb report --days 30
```

常见类型：`session_start` · `technique_hit` · `note` · `deposit` · `deposit_rejected` · `todo_add` · `todo_done` · `habit_upsert` · `import` · `promote` …

技巧升强度：

```bash
python3 .../engine/kb technique bump <id> --to repeated
```

---

## 新仓库接入 Fact

未 import 时开场会提示。按需：

```bash
python3 .../engine/kb import "<检出路径>"
```

不 import 仍可用 note / deposit / todo / habit / 技巧命中——只是没有该仓 Fact 投影。

---

## 出问题

```bash
python3 .../engine/kb doctor
bash .../scripts/install_personal.sh
python3 .../engine/kb help <主题>
```

Cursor 仅有命令投影、无 hooks 时见 [`docs/adapters/cursor.md`](../../docs/adapters/cursor.md)。

---

## 明确不做（避免日常又补流程）

- 日常不改 hook 形态 / 平台叙事  
- 向量检索、跨设备 Fact 同步、对外收费  
- 自动清空检出 `.claude` 或自动 fork 整套 claude_plugins  
- Cursor 自动命中 **不是** 个人版完成条件（Claude Code hooks 是）