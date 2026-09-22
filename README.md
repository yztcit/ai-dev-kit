# ai-dev-kit

跨项目通用的 Claude Code 能力沉淀仓库。这里的每个 plugin 都**不含任何业务/团队语境**，任何项目、任何团队装上就能用。

## 分层定位

| 层 | 仓库 | 特征 |
|---|---|---|
| 公共通用（本仓库） | `yztcit/ai-dev-kit` | 不含业务、不含团队语境，哪里都能用 |
| 团队共用 | `yztcit/claude_plugins`（marketplace `tal-tools`） | TAL 团队约定、内部工具 |
| 项目业务 | 各项目 `.claude/` | 绑死本项目（如 ai_eyes / xpy_interact） |

依赖单向：`项目业务 → 团队共用 → 公共通用`，禁止反向引用。

## 晋升规则

能力从下层晋升到本仓库前，必须通过**去语境化**检查：

> 残留某个项目/团队的影子（具体机型、业务术语、写死的路径、内部服务名），就还没资格进本仓库。

判据就一条：把插件放到一个完全陌生的项目里，它能否不依赖任何额外约定直接生效。

## video/：视频生成请求整理

`plugins/video` 提供跨项目通用的视频提示词整理能力，不含具体模型/产品语境。

| 组件 | 类型 | 说明 | 调用方式 |
|---|---|---|---|
| `video-pe` | Skill | 把文字与图/视频/音频素材引用整理成结构化视频生成请求（只格式化，不扩写剧情） | `/video:video-pe` |

## health/：资产健康巡检工具（流水线 A）

`health/` 是一套跨项目通用的健康巡检工具，通过解析本地会话转录（`~/.claude/projects/<项目>/*.jsonl`）算出每个**资产**（Skill 与 Agent）的冷门度/调用次数/重试率/失败次数，产出「例外队列」供人裁决，替代人工例行巡检。

> **未接入项见 [`health/BACKLOG.md`](health/BACKLOG.md)** —— 每项带**触发条件**（不是日期）。
> 不要定期通读；当某项的触发条件出现时再动手。

- `scan_skill_usage.py` — 转录解析（用量侧），产出调用统计 + 例外队列 + 窗口报告
- `scan_capability_layers.py` — 能力分层扫描（放置侧），产出晋升候选
- `decision_log.py` — 决策日志（人裁决落账 + 双向 override + ttl 重入队列）
- `skill-health-check.sh` — 巡检入口，有例外/晋升候选弹 macOS 通知
- `install.sh` — 幂等安装器，软链脚本 + 注册 launchd 定时任务（周一 09:15）

**两个维度，别混用**：用量侧回答「谁没人用」（驱动**退役**），放置侧回答「谁放错层」（驱动**晋升**）。三层体系当初只建了退役那一半——三类例外（冷门/高重试/高失败）全部指向退役，晋升方向信号为零。两侧共用同一份决策日志，也共用「**裁决后退出队列**」这条闭环。

换设备安装：`clone` 本仓库后 `./health/install.sh`。

### 覆盖范围

Skill（`name:"Skill"`）与 Agent（`name:"Agent"|"Task"` 的 `subagent_type`）都在统计内。**只统计命名资产**：Agent 调用缺 `subagent_type` 时（内置通用子代理）归入 `(general)`。子代理内部转录（`<session>/subagents/*.jsonl`）不参与统计——调用记录在父转录里，计入会重复。

失败信号取自该次调用自身 `tool_result` 的 `is_error`（按 `tool_use_id` 关联），不统计调用内部执行的其他工具错误——否则「跑测试的 skill」会被错误地判成高失败。

### 来源清点：例外队列只收「你能裁决的」

转录里只记名字、不记出处，于是内置与别人的插件会和你的资产混在同一张表里。实测后果：4 项「需人裁决」里有 2 项根本裁决不了——

| 资产 | 原始调用名 | 来源 | 能裁决吗 |
|---|---|---|---|
| `code-reviewer` | `dev:code-reviewer` | 你的插件 | ✅ |
| `panel` / `craft` | 裸名 | 项目层 | ✅ |
| `xpy-interact` / `agent-os` | 裸名 | 项目层 | ✅ |
| `run` / `Explore` / `Plan` | 裸名 | **内置**（磁盘上无对应文件） | ❌ |
| `frontend-design` | `frontend-design:frontend-design` | **官方 marketplace** | ❌ |

`asset_inventory.py` 按**文件系统**判定来源（`plugin:<marketplace>` / `project:<路径>` / `builtin`），规则：

- **例外队列只列 `project:*` 与自家的 `plugin:*`** —— 你去决定一件做不到的事，队列的可信度就没了。
- **内置与外部 marketplace 单独列出、标注「无需裁决」** —— 不悄悄吞掉，但不占用你的决策。
- `is_actionable()` 里 `EXTERNAL_MARKETPLACES` 默认只含 `claude-plugins-official`；自家/团队的 marketplace 一律视为可裁决。

**两个已知边界（勿当 bug）**：

1. **同名跨源无法分辨**。官方市场的 `feature-dev` 与团队 `dev` 插件**都有** `code-reviewer` → 该资产标为 `插件:claude-plugins-official+插件:tal-tools`。这是诚实输出：名字本身不足以定源。（转录里的前缀 `dev:` 本可区分，但裸名形式同样存在，故不假装能分辨。）多来源只要含一个自家来源即算可裁决。
2. **项目若在扫描根之外，会被归为「内置」而静默排除出队列**。故输出里始终打印扫描根（`--root`，默认 `~/workspace`）——项目不在这个根下时先改它，否则你会看到一份「无例外」的假阴性。

### 两个配置不变量（改了会静默失效）

1. **`--cold-days` 必须严格小于转录保留期**（Claude Code `cleanupPeriodDays`，默认 30 天）。等于或超过保留期时，资产在「够冷」之前记录就已被清理，冷门**永远判不出来**——报告会一直显示「无例外」，看起来健康，其实是没有数据。脚本检测到该配置会直接告警。
2. **`--days` 取保留期本身即可**（默认真实配置用 30）。取更大值不会拿到更早的数据（那部分已被清理），只会让窗口显得更长。

### 快照（对抗源过期）

源转录只有约 30 天寿命，窗口内证据会持续流失。`--snapshot FILE` 把每轮聚合追加成 append-only JSONL（默认 `report/skill-usage-history.jsonl`，gitignore），使时间序列不随源过期而丢失；并与上一轮对比报出**退出窗口**的资产。仅在窗口一致时对比——窗口不同则「退出」只是口径差异，不是信号。

> 退出窗口的语义是**中性**的：既可能是真冷门，也可能是记录刚好过期。这正是必须显式报出来的原因——把两者都读成「无例外」，就是假阴性。

### 怎么查「需要裁决什么」

三种入口，按场景选：

**① 等通知（常态）** —— 每周一 09:15 自动跑，**只在有待处理项时**弹 macOS 通知，文案就是一行摘要：

```
Skill 健康巡检：需裁决
4 个待裁决：panel、run、xpy-interact、frontend-design
```

通知点不出明细（`display notification` 不支持指定点击目标，见下「平台边界」），看到后走 ② 或 ③。

**② 打开报告（看全量明细）** —— 每次巡检把完整结果追加到：

```
<仓库路径>/health/report/skill-health-report.txt
```

文件按时间倒序追加，每次一个 `=== 时间戳 ===` 段，段内含两块：**用量侧例外队列**（附可照抄的裁决命令）与**放置侧晋升候选**。

**③ 手动查（随时，不落报告）** —— 两条命令，都是只读：

```bash
# 待裁决的例外（冷门 / 高重试 / 高失败）+ 每个例外的裁决命令
python3 ~/.claude/scripts/scan_skill_usage.py --exceptions-only

# 晋升候选（跨项目重复、共享层缺位的能力）
python3 ~/.claude/scripts/scan_capability_layers.py

# ttl 到期、需重新审视的 keep（只跟已落过的裁决有关）
python3 ~/.claude/scripts/decision_log.py due
```

**三份清单分属两个维度，别混**：

| 清单 | 来源 | 要你决定什么 |
|---|---|---|
| 例外队列 | 用量侧 | 这个能力**留还是下架** |
| 晋升候选 | 放置侧 | 这个能力**上移还是不动** |
| `due` | 决策日志 | 之前 keep 的，**还要不要继续留** |

### 裁决怎么用（`decision_log.py`）

自动化只 flag，动作永远是人——但必须带理由与时效，并记成决策日志（**决策本身也是数据**）。命令入口 `~/.claude/scripts/decision_log.py`（软链到本仓库 `health/decision_log.py`）。

| 子命令 | 用途 |
|---|---|
| `record` | 落一条裁决（唯一会写盘的） |
| `list` | 看已有裁决（只读） |
| `due` | 列出 ttl 到期、需重新审视的 keep（只读） |

`record` 的参数：

| 参数 | 必填 | 说明 |
|---|---|---|
| `--skill` | ✅ | 资产名，即例外队列里的那个名字 |
| `--action` | ✅ | 两个维度共用一份日志，动作词表按问题类型分：**用量侧** `keep` / `retire`（留着 / 下架）｜**放置侧** `promote` / `hold`（上移共享 / 保持本地） |
| `--reason` | ✅ | 为什么。写清楚——它是下次复查时唯一的上下文 |
| `--override` | | 标记这是**推翻**评测结论的人工判断 |
| `--scenario-tag` | | override keep 时标注场景（如「某机型兼容」） |
| `--ttl YYYY-MM-DD` | | 仅 keep 生效：到期自动重回例外队列，避免「暂留变永久」 |
| `--by` | | 默认取 `$USER` |

两个方向都要记：

```bash
# 评测报冷门，但你知道它是按需调用 → keep，并定复查日期
python3 ~/.claude/scripts/decision_log.py record \
  --skill panel --action keep --reason "评审类 skill，按需调用不是冷门" --ttl 2026-12-31

# 评测还行，但你判断该下架 → retire + override（理由回灌评测，修正盲区）
python3 ~/.claude/scripts/decision_log.py record \
  --skill xxx --action retire --override --reason "与官方同类重复，我们的版本无增量"
```

复查：

```bash
python3 ~/.claude/scripts/decision_log.py list    # 全部裁决
python3 ~/.claude/scripts/decision_log.py due     # ttl 到期的 keep，需重新审视
```

**裁决会关闭队列（这是闭环的关键一步）**：两个扫描器都**先查裁决再入队**——

- 已裁决且未到复查日 → **退出例外队列**，不再进通知。不这么做的话「裁决完还在催」，通知每周重复同一件事，最后被整体无视。
- `keep` / `hold` 可带 `--ttl`：到期才重回队列（避免「暂留变永久」）。不带 ttl = 永久保留，这是合法选择。
- 已裁决的资产**滑出时间窗口也会静音**：对「keep、按需调用」的资产，滑出是预期而非新闻（实测 `panel`：裁决时已 28 天未用，次周必滑出）。要定期复查请用 `--ttl`，那是它的职责。
- `promote` 是**有执行动作**的裁决（要把能力真搬进共享层）：不再进通知，但输出里标注「⚠️ 待执行：上移到共享层」，避免搬运被遗忘；真搬完之后候选自然不再被检出。

**落盘与共享范围**：`health/report/skill-decisions.jsonl`

- **决策日志共享**（`.gitignore` 里单独放行 `!report/skill-decisions.jsonl`）。它是**人工判断**，不是遥测：低频、高价值、append-only，换设备/换人不该从零重新裁决一遍。每行自带 `decided_at` 与 `by`，故配 `merge=union`（见 `health/.gitattributes`）——两人各自追加时两边都不丢行。
- **巡检报告与快照不共享**（`report/*`）：派生自本机转录，机器特定、每周重生成、噪声大。

> 巡检报告的每个例外下面会直接列出对应的 `record` 命令行，照抄改 `action` / `reason` 即可。

### 放置侧：晋升候选（`scan_capability_layers.py`）

判据是确定性的，不需要 LLM：**某能力在 ≥2 个不同项目的项目层各自存在，而共享层（已装 marketplace 的载荷）没有它** → 它就是「已被多个项目独立重复、本该共享」的晋升候选。

- 内容的两种形态分开标注：**逐字相同**（最直接的通用证据）、**已分叉**（各项目已开始各自维护，漂移成本正在产生）。
- 用 git remote 归并「同一项目的多份副本」，避免把副本误算成两个项目。
- **只 flag，不做动作**。去语境化是语义动作，由人裁决后手工上移（检测与决策分离）。

**已知边界（勿当 bug）**：判据按**名字**匹配，看不见**近义不同名**的覆盖。例如项目层的 `requirement-analysis` 与团队层的 `solution-design` 职责相近却不同名 → 会被报为候选，实际可能只需人工确认「已覆盖」。这正是它只出候选、不出结论的原因。

### 平台边界（当前只支持 macOS）

| 部件 | 跨平台？ | 说明 |
|---|---|---|
| `scan_skill_usage.py` / `scan_capability_layers.py` / `decision_log.py` | ✅ | 纯 Python，Windows 上可直接跑 |
| 调度（`install.sh`） | ❌ macOS | 生成 launchd plist |
| 通知（`skill-health-check.sh`） | ❌ macOS | `osascript` |

**结论：Windows 目前收不到通知，也没有自动巡检**——不是「需要授权」，是这两块平台特定部件根本没写。Windows 用户今天能做的只有手动跑 Python 脚本。

补它所需的最小工作（**尚未实现**）：一个 `skill-health-check.ps1`（跑同一对 Python 脚本 → 追加报告 → 弹 toast）+ 对应的一次性计划任务注册（`schtasks` / `Register-ScheduledTask`）。**为什么没顺手做**：本机无 Windows / 无 pwsh，无法验证任何一行；而一个静默失效的调度注册比没有更糟（会让人以为监控已开）。要上的话需在 Windows 上实跑一次确认。

## 当前状态

- `plugins/video` 已落地：`video-pe` 视频生成请求整理。
- `health/` 已落地（流水线 A），产出写入 `health/report/`。**其中决策日志 `skill-decisions.jsonl` 共享**（人工判断，跨设备/跨人累积），巡检报告与快照不共享（派生自本机转录）。覆盖已从「仅 Skill」扩到「Skill + Agent」，并补齐失败信号、快照与晋升候选检测。
- **未落地**：流水线 B（回归门禁，judge 打分 + 冻结基线）、流水线 C（官方/依赖漂移检测）。B 是唯一能产出「更好」的环节——A 只能告诉谁没人用，说不出谁做得好。
