# 个人 AI 助手（experience 0.3）产品设计定稿

日期：2026-11-20  
状态：**已批准**（2026-11-20）→ 实现计划见 `docs/superpowers/plans/2026-11-20-experience-personal-0.3.md`  
产品名（对内）：experience 个人版 0.3  
一句话：**本机个人 AI 助手操作系统**——知识复利 + 项目投影 + 轻量待办/规划/复盘；你出意图并日常用，系统用日志与开场展示证明生效；可一键关闭；换 AI 工具不搬家。

---

## 0. 产品定位与分工

### 0.1 解决什么

会话一换、工具一换，结论与规范就丢；同一规范在多项目各抄一份；待办散落聊天；做完的设计/实现无法变成「下次可借」的公共能力。本产品把「记得住、用得上、看得见、关得掉」收成本机闭环。

### 0.2 不做什么

- 不做 Todoist/日历 SaaS、向量检索、全量会话自动沉积、对外收费平台。  
- 不做每个 IDE 完整自动注入对等（注入是加速器，不是完成定义）。  
- 不以「提案过目」为质量闸——质量看 **日志、开场展示、report**。

### 0.3 分工

| 角色 | 负责 |
|---|---|
| 用户 | 提想法；日常用 `/kb-*`；按剧本配合验证 |
| 助手 / 仓库 | 设计细节、实现、目录/文档分类、验收与迭代；不等用户补流程 |

### 0.4 成功判据（发版后 7 天可证伪）

1. `kb doctor` 全绿；`/kb-off` 后开场无注入且 doctor 显示 DISABLED；`/kb-on` 恢复。  
2. 已接入仓开会话时，开场可见 **kb 生效条**（见 §5）。  
3. report 能统计 note/deposit/todo/hit；单次 deposit 拆分条数 ≥ 2；无反例 Technique 被拒写。  
4. 分支 import 后，`facts/.../base` 与 `branches/<名>` 分层存在，无静默互相覆盖。  
5. 至少一条「项目设计/实现」经去语境化进入 `methods-personal`，report 可指向晋升候选。

---

## 1. 整体架构

### 1.1 四域一核 + 开关

```
 /kb-* 与别名（适配器：Claude / Cursor / 他工具模板）
                    │
                    ▼
              kb CLI（可 off）
         写入口 · 校验 · 事件 · 展示载荷
                    │
     ┌────────┬─────┴──────┬──────────┬─────────┐
     ▼        ▼            ▼          ▼         ▼
  知识复利  项目投影    工作管理    可观测性   公共约定
  scratch   facts/      todos/     logs/     conventions
  methods-  base+       plan/retro events    （AI-dev-kit）
  personal  branches/              doctor
            import/sync            status
```

### 1.2 复利闭环（回答：项目/对话信息怎么成为复利？）

复利 ≠「存进文件」；必须走完 **再用到 + 可度量变强**：

```
 对话/项目材料
       │
       ├─ /kb-note ──────────────► scratch（未定稿）
       ├─ /kb-deposit ───────────► 拆条：Fact | Technique | 项目Plan文档
       ├─ /kb-import ────────────► 本仓 .claude 树 → facts（按分支分层）
       └─ /kb-todo ──────────────► 待办（可到期；不进知识复利主链）
       │
       ▼
 下次会话：SessionStart / 命中
       │  Fact 投影进 .claude；Technique 按话术注入；逾期 todo 展示
       ▼
 使用产生事件（hit / sync / todo_done…）
       │
       ▼
 /kb-bump · /kb-retro · /kb-promote
       │  强度升档；去语境化后升公共层
       ▼
 更强的下一次命中  ←── 这才叫复利
```

| 阶段 | 你做什么 | 系统做什么 | 如何证明 |
|---|---|---|---|
| 捕获 | `/kb-note` 或说话术 | 写 scratch + 事件 | report.note↑ |
| 入库 | `/kb-deposit` / `/kb-import` | 校验、分流、落盘 | deposit 条数、facts 树 |
| 生效 | 正常开会话 | 投影 + 命中 + 开场条 | 开场展示、technique_hit |
| 变强 | `/kb-bump` / 复盘 | 升强度、列晋升候选 | strength、promote 事件 |

**对话里随口的信息**：不自动全量沉积；只有你触发 note/deposit/todo 才进链。  
**项目里的文档**：import 进 Fact 投影链；其中「可去语境」部分经 deposit/promote 进 Technique/公共层才算跨项目复利。

### 1.3 对象分流

| 对象 | 是什么 | 不是什么 |
|---|---|---|
| Scratch | 未定稿草稿 | 待办 / 最终知识 |
| Fact | 仅本仓现实 + 本仓 `.claude` 树 | 跨仓规范 |
| Technique | 去语境做法（须反例） | 绑死某仓路径的说明 |
| 项目 Plan 文档 | 仓内 `.claude/plans`（`kind`） | 个人待办 |
| Todo | 可勾选、可 due | 知识条目 |
| Conventions / 公共插件 | 全局可分享资产 | 某仓私货 |

口诀：要勾掉/带日期 → Todo；教以后怎么做且跨仓 → Technique；只本仓真 → Fact；没想清 → Scratch；多类一起收 → Deposit。

---

## 2. 目录与文档分类（为扩展打底）

### 2.1 本机数据根 `~/.local/share/dev-memory/`（运行时，不进公开 git）

```
dev-memory/
  index.json                 # 已接入仓、never_remind、enabled 全局开关镜像
  state.json                 # kb on/off、版本、最后 doctor
  scratch/                   # 草稿
  todos/                     # 个人待办
    items.jsonl
  habits/                    # 跨仓个人习惯卡 + index.json
  facts/<host>/<path>/       # 按仓库身份
    kb.yml
    base/                    # 主干共用（对应主分支现实）
    branches/<branch>/       # 覆盖层：同路径覆盖 base，仅该分支可见
  methods-personal/          # 个人技巧卡 + index.json
  inbox/{facts,methods}/     # 暂存（可选）
  logs/events.jsonl          # 唯一反馈账本
  install-marker.json
```

**扩展约定：** 新域只加顶层目录（如 `journals/`），不塞进 `facts/`；新事件类型只追加，不改旧字段语义。

### 2.2 仓库内 `plugins/experience/`（产品代码与权威命令正文）

```
plugins/experience/
  PERSONAL-USE.md            # 唯一日常入口
  README.md                  # 开发者入口
  commands/kb-*.md           # / 命令权威正文（投影到各工具）
  skills/{note,deposit,...}/ # 自然语言别名
  hooks/                     # Claude SessionStart / PromptSubmit
  scripts/install_personal.* # 安装 / 投影 / 可含 off 恢复说明
  engine/                    # kb CLI 与库（唯一写入口）
    tests/
  seed_techniques/           # 可分享种子 → 首次拷到 methods-personal
  techniques/index.json      # 公开可分享索引（晋升目标之一）
```

### 2.3 仓库文档层（AI-dev-kit 根）

```
docs/
  superpowers/specs/         # 产品设计定稿（本文件）
  superpowers/plans/         # 实现计划
  adapters/<tool>.md         # 他工具薄适配说明
docs/design/EXPERIENCE-COMPOUNDING.md  # 经验复利原理（与 0.3 对齐）
DESIGN.md                    # 三层准入与防腐不变量
health/BACKLOG.md            # 推迟项与触发条件
plugins/conventions/         # 全局规范唯一事实源
```

**分类纪律：** 日常用法不进 DESIGN；实现计划不进 PERSONAL-USE；业务仓语境不进 `docs/` 与 conventions。

---

## 3. 分支 import（回答：不同分支重复且不同的文档？）

### 3.1 模型（已有引擎语义，0.3 写清产品规则）

Fact 的「分支」= **代码检出当前 git 分支**，不是另起一套 git：

```
facts/<身份>/
  base/                      # 主干（主分支）共用文档
  branches/feature-x/        # 仅 feature-x 检出可见；同相对路径整文件覆盖 base
```

合成：`desired = base ∪ overlay(branches/<HEAD>)`（同路径以分支文件为准）。

### 3.2 import 时怎么处理「同路径、不同内容」

| 情况 | 行为 |
|---|---|
| 在 **主分支** import | 写入 `base/`；若与已有 base 同路径内容不同 → 覆盖 base，并打 `import` 事件（含 diff 指纹） |
| 在 **功能分支** import，文件与 base **相同** | 不写入 branches（避免无意义重复） |
| 在 **功能分支** import，文件与 base **不同** | 写入 `branches/<当前分支>/` 对应路径；**绝不**默默改 base |
| 两功能分支各改同一路径 | 各有各的 `branches/<A>`、`branches/<B>`；互不合并 |
| 功能分支合入主干后 | `/kb-promote`（或 `kb promote`）把覆盖层文件升到 base，再删多余 overlay；未 promote 则主干仍见旧 base |

**不做：** 自动三路 merge 文档正文；用 LLM 静默「揉成一份」。冲突的权威动作是 **promote / 手工选留 + 事件**。

### 3.3 命令

- `/kb-import`：按当前 HEAD 执行上述规则。  
- `/kb-sync`：按当前 HEAD 投影 `base∪branch` 到检出 `.claude`。  
- `/kb-status`：展示身份、分支、overlay 文件列表、kb on/off。

---

## 4. 一键关闭 / 打开（回答：回归无 kb 形态）

### 4.1 语义

| 命令 | 效果 |
|---|---|
| `/kb-off` | **关闭生效**：hooks 变为 no-op（或从 settings 禁用 experience 段）；不再投影/命中/注入逾期；**不删** `dev-memory` 数据 |
| `/kb-on` | 恢复 hooks/投影；跑一次 doctor |
| `/kb-uninstall`（可选，0.3.x） | off + 移除命令投影与 skill 软链；数据仍保留除非加 `--purge` |

实现要点：

- `state.json`: `{ "enabled": false, "disabled_at": "..." }`。  
- hooks 入口第一行读 enabled，false 则静默退出（或打印一行 `kb: off`）。  
- install 写入的 hooks **保留**，靠开关短路，避免 off/on 反复改 settings 易坏。  
- doctor：off 时总体状态为 `DISABLED`（不算失败红灯，或单独色）；列出「当前未注入」。

**回归无 kb：** `/kb-off` 后行为与未装 experience 注入时一致；项目 `.claude` 若曾被 sync 成投影，off **不自动还原历史手工版**（避免丢数据）；需要时从 `.kb-backup` 恢复（已有备份机制则文档写明）。

---

## 5. 日常如何知道生效了（回答：有没有展示？）

### 5.1 开场固定展示（主信号）

每次 SessionStart（kb on 且已接入仓）注入一行可读状态，例如：

```text
[experience] kb ON · znxx_pad_aivoice@feature-x · facts:base+3overlay · techniques:hit候选2 · todos逾期:1
```

未接入：`[experience] kb ON · 本仓未 import · 仅技巧/待办可用 · /kb-import 可接入`  
关闭：`[experience] kb OFF · 输入 /kb-on 恢复`（若 hook 仍在；完全卸掉则无此行——那就是「无 kb 形态」）。

### 5.2 主动查询

| 命令 | 展示什么 |
|---|---|
| `/kb-status` | on/off、仓身份、分支、overlay、最近 sync、技巧数、逾期待办 |
| `/kb-doctor` | 安装健康 |
| `/kb-report` | 近 N 天复利与待办数据 |

### 5.3 间接证明

命中时上下文出现技巧卡；`.claude` 出现 `.kb-state.json`；`events.jsonl` 增长。  
**不以「感觉有用」为准**；以开场条 + status + report 为准。

---

## 6. 项目设计/实现 → 公共复利（回答：以后借鉴怎么落盘？）

### 6.1 晋升阶梯

```
 项目会话/文档
    → /kb-deposit（Fact 留仓内；可复用思路 → Technique hypothesis）
    → 多次命中 /kb-bump → used → repeated
    → 去语境化审查（去仓库名/路径/业务专名）
    → /kb-promote
         ├─ 个人仍用：留 methods-personal（已足够跨仓）
         ├─ 规范类：写入 plugins/conventions（或 PR）
         └─ 流程/技能类：写入 plugins/experience/seed_techniques
              或新 skill/plugin，并更新公开 techniques/index.json
```

### 6.2 什么配晋升

| 材料 | 先落哪 | 晋升条件 |
|---|---|---|
| 某需求的设计思路、实现步骤、踩坑 | deposit → Technique（含反例）或 reference 计划 | `repeated` + 去掉项目专名后仍成立 |
| 通用代码/协作规范 | 直接对 conventions 提改，勿进多仓 Fact | 去语境化通过 |
| 仅本 App 模块结构 | Fact only | **不晋升** |
| 一次性实验 | scratch / 勿 bump | 不晋升 |

### 6.3 `/kb-promote`（0.3 必做最小版）

菜单注释：【经验库】升到可分享层：把已验证的个人技巧去语境化后，复制/导出到 AI-dev-kit 的 seed 或 conventions 候选目录，并打点；不自动打 PR。

- 输入：technique id。  
- 检查：strength∈{used,repeated}；正文无未替换的业务专名（简单启发式 + 助手人工清一次）。  
- 输出：写入 `plugins/experience/inbox-promote/` 或 `seed_techniques/` 候选；事件 `promote`；由维护者后续 PR。

---

## 7. 命令面总表（前缀 `kb-`）

注释格式：`【经验库】` + 口语结果 + 会改/不会改什么。

| 命令 | 菜单注释（摘要） |
|---|---|
| `/kb-note` | 先存草稿到本机 markdown；不改项目配置、不建技巧/待办 |
| `/kb-deposit` | 会话拆成多条事实/做法/仓内计划文档并校验入库 |
| `/kb-import` | 当前分支把 `.claude` 收进 kb（按 base/覆盖层规则） |
| `/kb-sync` | 用 kb 刷新当前检出 `.claude` |
| `/kb-todo` | 记/勾待办，可带截止日期 |
| `/kb-plan` | 把目标拆成待办写入清单（长文设计仍走 deposit） |
| `/kb-retro` | 按日志复盘并建议 bump/todo/promote |
| `/kb-bump` | 技巧升档或标否定 |
| `/kb-promote` | 个人技巧升到可分享候选目录 |
| `/kb-status` | 看 kb 是否 ON、本仓/分支/逾期/技巧概况 |
| `/kb-report` | 近 7 天数据 |
| `/kb-doctor` | 安装体检 |
| `/kb-help` | 查某能力怎么用：`/kb-help deposit`（见 §7.1） |
| `/kb-habit` | 记跨项目个人习惯，开场注入；不改项目 Fact、不改 claude_plugins 源码（见 §7D） |
| `/kb-off` / `/kb-on` | 一键关闭/恢复生效（不删数据） |

### 7.1 `/kb-help`（帮助）

- 用法：`/kb-help` 总览；`/kb-help <主题>` 如 `note` `deposit` `import` `todo` `off` `promote` `claude_plugins`。  
- 行为：输出该能力的「何时用 / 不要用 / 会改什么 / 一条最短例子 / 相关命令」；内容来自 `commands/kb-*.md` 与 PERSONAL-USE 的同源片段，**禁止另写第二套说明**。  
- 前缀仍用 `kb-`（与产品一致）；若工具允许，可把描述写成「【经验库】帮助：查 note/deposit/import…怎么用」。

---

## 7A. 费用与占用（kb 会增加 AI 费用吗？）

### 7A.1 结论（先说清楚）

| 项 | 影响 |
|---|---|
| **API/订阅费用** | **不另收「kb 费」**。kb 本身是本机 CLI + 文件；计费仍是你用的 Claude/Cursor 模型。 |
| **会多耗一点上下文** | 会。开场状态行、命中技巧卡、Fact 投影进对话，都会占 **输入 token**。 |
| **本机磁盘/CPU** | 很小：markdown + jsonl；hooks 为短脚本，秒级。 |

### 7A.2 消耗来源（可控）

| 来源 | 典型量级 | 怎么控 |
|---|---|---|
| 开场 `[experience] kb ON …` 一行 | 可忽略 | 保留 |
| Technique 命中注入全文 | 中：每卡数百～数千 token | 低强度只列清单；`contradicted` 不灌；`/kb-off` 全关 |
| 投影后的 `.claude` 被模型读取 | 随你打开的文件而定 | 仓内只留必读；大计划用 reference 迁出 |
| 你跑 `/kb-deposit` 等 | 与普通让模型整理文档同级 | 按需触发，非每句自动 |

**不会：** 后台偷偷连云做 embedding；不会每键上传全库。  
**感知贵时：** `/kb-off` 立刻回到无注入；或减少高 hit 卡的全文灌入（report 里看命中次数再 bump/精简卡）。

---

## 7B. `claude_plugins` 还要吗？怎么参与本产品？

### 7B.1 还要用

`claude_plugins`（`dev` 插件：dev-flow / solution-design / code-review / agents…）是 **Playbook（怎么干活的流程）**；`experience`/`kb` 是 **记忆与复利（记得住、用得上）**。两者互补，**不互相替代**。

| | claude_plugins | experience (kb) |
|---|---|---|
| 解决 | 研发流程怎么走、谁来审查/实施 | 跨会话/跨仓知识与待办 |
| 形态 | Skill + Agent | 本机库 + hooks + `/kb-*` |
| 安装 | marketplace 装 `dev`（可选第二行） | `install_personal` / experience 插件 |

### 7B.2 如何参与 0.3 产品

1. **推荐组合（文档写明）：** 先装 experience（kb），需要流程时再装 `dev@claude_plugins`。  
2. **命中顺序：** SessionStart 先 kb（Fact/技巧/待办展示）；用户调用 `/dev:dev-flow` 等走 Playbook；流程中的结论用 `/kb-deposit` / `/kb-todo` 落盘。  
3. **晋升：** Playbook 跑出的通用做法 → Technique → `/kb-promote`；不要把业务 Fact 写进 claude_plugins 仓。  
4. **帮助：** `/kb-help claude_plugins` 说明「流程用 dev-*，记忆用 kb-*」。  
5. **不做：** 0.3 不把 claude_plugins 合并进 AI-dev-kit；不改其插件名；避免双开导致同一约定重复加载（conventions 仍只走 AI-dev-kit 那条）。

### 7B.3 能不能用 kb「按个人习惯定制 claude_plugins」？会自动生成吗？

**短答：可以「按你的习惯改行为」，但 0.3 不自动改写/生成 claude_plugins 插件包。**

| 做法 | 0.3 | 说明 |
|---|---|---|
| kb 习惯 + 技巧在开场/命中时注入，**盖在** Playbook 之上 | ✅ | 你跑 `/dev:dev-flow` 时，模型已带着个人习惯；等于「定制后的行为」，无需改插件源码 |
| `/kb-promote` 把反复验证的流程片段导出为 **skill 候选**（inbox-promote） | ✅ 半自动 | 生成的是候选文件，**人审阅后**再 PR 进 claude_plugins 或 experience |
| 后台根据聊天 **自动重写** `claude_plugins` 里的 Skill/Agent | ❌ | 共享 Playbook 被个人习惯污染；难回滚；违反「公开仓无业务/个人影子」 |
| 一键「从 kb 生成我的整套 fork 插件」 | ❌ 非目标 | 维护成本高；用「注入 + 候选晋升」更稳 |

产品表述：**kb 定制的是「助手怎么对你行事」，不是「自动长出一份私有 claude_plugins」。**  
若某条习惯应成为全员流程，走 promote → 人工合入 Playbook；其余永远留在本机 `methods-personal` / 习惯层。

---

## 7C. import 之后，本地文档能否删一部分？（只留项目/分支必留）

### 7C.1 原则

**kb 里的 `facts/.../base|branches` 才是个人权威；** 检出里的 `.claude` 在 personal 投影模式下是 **构建产物**（sync 可再生成）。  
但若 `.claude` **进了团队 git、别人还要靠它**，你删的是共享资产——**不能只按个人方便删。**

### 7C.2 可以删 / 不可删

| 可以考虑删或挪走（个人侧） | 必须留 |
|---|---|
| 已确认进 kb 且可 `/kb-sync` 还原的**个人**重复稿 | 团队共享、且未以团队流程改权威源的 `.claude` 文档 |
| 已完工且已 deposit 的 exec 计划（按 EXPERIENCE plans TTL） | 当前分支仍依赖、合入前还要用的分支 overlay 对应内容（应在 `branches/<名>`，检出可 sync） |
| 与 conventions / 个人 Technique 重复的「又抄一份规范」 | 源码、非 `.claude` 的产品文档、密钥、CI 所需文件 |
| scratch 里已沉淀完的草稿 | 唯一副本且尚未 import 成功的文件 |

### 7C.3 推荐操作顺序（防丢）

1. `/kb-import`（各需要的分支都 import 过）。  
2. `/kb-status` 确认 base/overlay 列表完整。  
3. 另开目录或 git 确认可 sync 还原后，再删检出里的**个人冗余**。  
4. 团队仓：只删「个人备注/重复规范」，或改为不提交个人层；共享正文改 kb 权威需团队约定（team-tracked overlay）。  
5. 删前打事件或至少本地备份；**禁止**脚本默认「import 后自动清空 `.claude`」。

### 7C.4 产品能力（0.3）

- `/kb-help import` 含「删本地前清单」。  
- 可选 `kb gc-local --dry-run`（0.3.x）：列出「与 kb 哈希相同、可安全标为投影重复」的文件；默认 dry-run，不自动删。

---

## 7D. 个人习惯与「更懂用户」

### 7D.1 目标

「更懂」= **稳定偏好可注入 + 用数据校正**，不是黑盒用户画像，也不是全量窃听会话。

### 7D.2 习惯记在哪

| 层 | 路径 | 记什么 |
|---|---|---|
| **习惯卡（主）** | `dev-memory/habits/` + `habits/index.json` | 跨仓个人偏好：沟通风格、提交纪律、何时问你、语言、审查口味…（去项目名） |
| **技巧卡** | `methods-personal/` | 「怎么做」的可复用步骤（须反例） |
| **全局用户层** | `~/.claude/CLAUDE.md`（或软链到个人私有 git） | 极短、总是要带的几条硬偏好（与 DESIGN §八 对齐） |
| **项目 Fact** | `facts/<身份>/` | 只在本仓成立的约束——**不算个人习惯** |

### 7D.3 怎么写入（显式为主）

| 方式 | 命令/动作 | 说明 |
|---|---|---|
| 你直接说 | `/kb-habit` 或「记住我习惯：…」 | 写入/更新 habits 卡；强制 `event:habit_upsert` |
| 沉淀时分流 | `/kb-deposit` | 识别「这是偏好不是项目事实」→ 进 habits，禁止写进当前仓 Fact |
| 复盘建议 | `/kb-retro` | 根据纠正/重复命中 **提议** 习惯条；你说「记下」再写（0.3 不默认静默改习惯） |

**不做：** 正则扫全部聊天自动抽习惯；不经事件的静默改 `CLAUDE.md`。

### 7D.4 弱信号（只进报告，不直接改习惯）

从 `events.jsonl` 统计，供 `/kb-retro` / `/kb-report` 使用：

- 你纠正助手的次数与主题（若会话内 deposit 时标注 `correction`）  
- 技巧 `contradicted` / 低 hit  
- 常在某类 todo 上逾期  

→ 输出「候选习惯」列表；**写入仍要 `/kb-habit` 或确认一句**。

### 7D.5 怎么「用上」从而更懂

1. SessionStart（kb ON）：注入 **habits 摘要**（有上限，如 ≤N 条 / ≤K token）+ 开场状态行。  
2. 话术命中 Technique（做事方法）。  
3. 与 Playbook 叠加：dev-flow 跑流程时已带习惯，无需改插件。  
4. 度量：habit 注入次数、用户是否 `/kb-habit` 否定某条、report 里「习惯稳定度」。

### 7D.6 `/kb-habit` 菜单注释

【经验库】记个人习惯：把跨项目偏好写成习惯卡（如「提交前等我确认」「回答先给结论」）；会进入以后所有会话的开场摘要，不写进某个项目的 Fact，也不改 claude_plugins 源码。

---

## 8. 引擎与适配器（摘要）

- 唯一写入口：`kb`；命令正文只教调哪个子命令。  
- deposit 整单校验；分支 import 规则见 §3。  
- todo：`todos/items.jsonl`；提醒仅 report/开场，不接系统通知。  
- Claude：hooks+commands+skills；Cursor：命令投影；他工具：`docs/adapters/`。  
- off 时 hooks 短路；数据保留。

---

## 9. 验证与迭代

| 级 | 动作 | 通过 |
|---|---|---|
| L0 | pytest | 全绿 |
| L1 | doctor | ok 或明确 DISABLED |
| L2 | 15min 剧本 | 含：开场条可见、note/deposit/todo、off 后无注入、on 恢复、分支 import 不写坏 base |

**剧本要点：** doctor → status 见 ON → note → deposit≥2 → todo+due → report → off → 再开会话无事实注入 → on → 恢复。

日产事件；周 retro；0.3.x 只修剧本洞。

---

## 10. 实现切片

1. 目录：`state.json`、`todos/`、`habits/`；engine：`note`、`deposit-apply`、`todo`、`habit`、`off/on`、`status`、`help`、分支 import、`promote` 最小版。  
2. SessionStart：开场条 + habits 摘要（token 上限）+ 逾期 todo。  
3. Commands 全表（含 `kb-help`/`kb-habit`）+ install 投影。  
4. Skills 别名；PERSONAL-USE：claude_plugins 分工、费用、习惯与「不自动生成插件」。  
5. 文档：EXPERIENCE/BACKLOG/adapters；import 删本地纪律。  
6. L0+L1+L2；`PRODUCT_VERSION=0.3.0`。

---

## 11. 自检

- [x] 复利闭环可叙述、可度量（§1.2）。  
- [x] 分支同路径不同内容 → overlay，不默默改 base（§3）。  
- [x] 一键 off/on，数据可留（§4）。  
- [x] 日常有开场展示 + status（§5）。  
- [x] 项目设计/实现 → 个人技巧 → 公共候选晋升路径（§6）。  
- [x] 本机与仓库目录分类清晰，便于扩展（§2）。  
- [x] 待办/规划/复盘在助手范畴且边界清楚。  
- [x] `/kb-help` 同源帮助。  
- [x] 费用/占用说明清楚（无额外 kb 云费；控注入 token）。  
- [x] `claude_plugins` 定位为 Playbook，与 kb 互补。  
- [x] import 后删本地有纪律与必留清单，无自动清空。  
- [x] 不自动生成/改写 claude_plugins；习惯用注入 + promote 候选。  
- [x] 个人习惯有归宿（habits）、显式写入、弱信号只进报告、开场有上限注入。
