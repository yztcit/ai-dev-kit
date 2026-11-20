# 经验复利体系 · 设计

版本 2026-11-19（定稿）· 路径 2026-11-20 迁入 `docs/design/`  
读者：独立评审者；无需事先了解某业务仓库  
地位：补齐 `DESIGN.md` §八「经验侧」；与放置侧（plugin/skill 分层）同构  
**配对计划（历史 V1，已 archive）：** [`../superpowers/archive/plans/2026-11-19-experience-compounding.md`](../superpowers/archive/plans/2026-11-19-experience-compounding.md)  
**现行产品：** [`plugins/experience/PERSONAL-USE.md`](../../plugins/experience/PERSONAL-USE.md) · 设计 [`../superpowers/specs/2026-11-20-personal-assistant-extreme-design.md`](../superpowers/specs/2026-11-20-personal-assistant-extreme-design.md)  
文档治理：[`../README.md`](../README.md)。

---

## 1. 目标

开发者在会话里探索现状、踩坑、形成可复用规则与能力后：

1. **下一会话不必从头探索同一类问题**（同项目或跨项目）。
2. **项目事实与经验技巧硬分离**：别人拿得到技巧，拿不到业务事实。
3. **先服务自己，形态可分享**：同事/朋友可装包；覆盖面变大后常见问题有高优先验过的方法。
4. **持续工作即持续积累**：捕获不靠「以后记得写文档」。

**非目标：** 业务知识上公开 Git；Fact 跨设备（现阶段无私有 git）；向量库作第一召回；一次性清理所有项目。

### 1.1 日常流程

```
做事
  ├─ 「记一下」→ scratch（本机草稿）
  └─ 「沉淀」
        → 拆成 Fact / Technique / plans 分类
        → 写入本机（技巧默认 hypothesis）
下次会话 → 自动带本仓 Fact + 匹配技巧（弱假设标明）
证伪     → 降权 / 例外，不靠事先审对
分享     → 只导出去语境且强度够的技巧；Fact 留本机
```

### 1.2 人工确认

**日常约每会话 0～2 次；重确认很少。**

| 时机 | 动作 | 频率 |
|---|---|---|
| 边做边记 | 「记一下」或点头 | 有料才说 |
| 收尾沉淀 | Fact 默认全收只剔错；技巧扫一眼；plans 标明 exec/reference | 每会话最多一次 |
| 对外发布 | 确认去语境 | 偶尔 |
| 例外队列 | 留/改/丢 | 低频 |

自动：开场命中、Fact 投影或加性注入、强度升降、过期 exec 清理提案。

---

## 2. 现状与缺口

| 资产 | 已有 | 缺口 |
|---|---|---|
| `claude_plugins` | Playbook 脊梁 | 会话技巧难低摩擦长入 |
| `AI-dev-kit` | 三层准入、防腐、例外队列 | 经验侧写入拆分 + 命中未闭环 |
| `personal-kb` | 多检出 Fact 投影 | 业务 Fact 进了 GitHub（违规）；叙事过重 |

根因：把「项目配置同步」和「经验复利」绑在同一公开仓。

**定案：** `personal-kb` **产品退役**；投影能力并入 `AI-dev-kit` 的 `experience` 插件。公开仓不再要求任何人 clone。

---

## 3. 对象与分层

沿用 `DESIGN.md`：公共 / 团队 / 项目，依赖单向，准入＝无项目/团队影子。

| 对象 | 含义 | 落点 |
|---|---|---|
| Scratch | 会话草稿，可含专名 | `~/.local/share/dev-memory/scratch/` |
| Fact | 仅本仓成立的现实 | `.../facts/<归一化remote>/{base,branches/<分支>}/` |
| Technique | 去语境可迁移技巧 | `.../methods-personal/` → 可晋升插件包 |
| Playbook | 分析/探索/排障/沉淀流程 | Skill（现有 `dev-flow` 等） |

### 3.1 Fact 分支

指**代码检出当前分支**，不是 Fact 目录的 git：

```
facts/<身份>/
  base/                    # 主干共用
  branches/<代码分支>/     # 整文件覆盖；仅该分支可见
```

SessionStart：`base ∪ branches/<HEAD>`。合入后 `promote` 或删覆盖层。

### 3.2 本机布局

```
~/.local/share/dev-memory/          # 非 git；不进公开 remote
  scratch/
  inbox/{facts,methods}/
  facts/<host>/<path>/{base,branches/…}/
  methods-personal/
  index.json                        # 已接入仓、永不提醒等
```

公开：`AI-dev-kit` 内 `plugins/experience`（引擎 + 沉淀 skill + 命中）+ 可选 `claude_plugins` Playbook。

---

## 4. 运行时

### 4.1 捕获与拆分

- 边标：「记一下」→ scratch。  
- 收尾：「沉淀」→ 扫会话 + scratch → **强制**拆 Fact / Method；plans 先标 `kind`。  
- Method 去语境失败 → 降级 Fact 或丢弃，不得进可分享层。

### 4.2 写入与强度（确认 ≠ 正确）

人确认＝「值得留档试用」，默认 `strength: hypothesis`。

| 信号 | 强度 |
|---|---|
| 写入 | `hypothesis` |
| 采用且未推翻 | `used` |
| 多会话重复 | `repeated` |
| 否定 / 按卡失败 / 与现实冲突 | `contradicted` |

- Fact：默认全收，只剔错。  
- Technique：确认写入；**反例栏**空则不得升到 `used` 以上。  
- 可分享层：仅 `repeated` + 去语境通过；`hypothesis` 禁止进公开包。

### 4.3 命中

1. 按 remote 处理本仓 Fact（投影或加性注入，见 §6）。  
2. Playbook：Skill description 路由。  
3. Technique：`index.json`（triggers + strength）。  
   - `contradicted`：不自动灌，只提示复核。  
   - `hypothesis`：弱注入并标明未验证。  
   - `used`/`repeated`：高置信直接读入；低置信 ≤5 条清单。  
4. 命中后发现冲突 → 提案，不静默改卡。  
5. V1 无向量检索。

---

## 5. Technique schema

```yaml
---
id: explore-before-edit
kind: technique          # technique | anti-pattern | heuristic
triggers: ["动手改代码前", "不确定现状"]
scope: personal          # personal | team | universal
verified_at: 2026-11-19
strength: hypothesis     # hypothesis | used | repeated | contradicted
---
## 情境
## 做法
## 反例
## 来源
```

Playbook 继续用 `SKILL.md`；卡片挂在相关 Playbook 索引下。

---

## 6. 仓模式与团队共存

### 6.1 扩仓（防遗忘）

| 机制 | 行为 |
|---|---|
| SessionStart | 未登记仓 → 提示 import / 跳过 / 永不提醒（不自动 import） |
| 沉淀 | 未接入则先接入向导 |
| check | 列出工作区未接入仓 |

### 6.2 `overlay` 模式

| 模式 | 条件 | 行为 |
|---|---|---|
| `personal` | `.claude` / `CLAUDE.md` 基本不进 git | 可投影到检出 |
| `team-tracked` | 团队已提交同名文件 | **禁止覆盖**已跟踪文件；Fact 加性注入 |

**git 已跟踪路径一律不投影覆盖。** 未跟踪 / gitignore 路径可管。

### 6.3 加性注入（team-tracked）

个人**不抢**团队 `CLAUDE.md` / `AGENTS.md` 文件名。内容进 `facts/.../base/PERSONAL.md`（或模块卡），SessionStart 追加进上下文；可选侧车 `.claude/personal/`（必须 gitignore）。

| 来源 | 进会话 | 改团队树 |
|---|---|---|
| 团队 CLAUDE/AGENTS/.claude | 是 | 否 |
| 本机 Fact / PERSONAL.md | 是（加性） | 否 |
| Technique / Playbook | 是 | 无关 |

冲突：两方都可见，标 `[personal-fact]`，分歧进例外。改团队文档 → PR 草稿，不本地覆盖。绝不自动 `git add` 个人 Fact。

---

## 7. plans 生命周期

| `kind` | 例子 | 命运 |
|---|---|---|
| `exec` | 改造执行稿 | 完工抽 Fact/Technique 后：删 / superseded（14 天）/ 决策档进 Fact |
| `reference` | 接入文档、协议、交接 | **不进删除 TTL**；迁出 plans/ 到 `facts/.../docs|handoff`（或团队允许的仓内 docs） |

未标 `kind` → 沉淀必须先问；自动化**禁止静默删**。同题仅一份 active/retained 现行正文。

巡检：无状态 >45 天待分类；exec superseded >14 天建议删；reference 未迁出 >30 天建议迁；缺继任只复核不删。

---

## 8. 分发

使用者：**一个** marketplace → `/plugin install experience@ai-dev-kit` → 本机建空 `dev-memory`。  
可选第二行装 Playbook（`dev`）。不是 clone 三仓。

装包不得下发任何业务 Fact。种子 Technique 仅 `universal` 去语境卡（可为 0 张）。

---

## 9. V1 范围与指标

**做：** 合规去业务；引擎迁入 experience；只迁 aivoice Fact 到本机；沉淀 skill；Technique index + 命中；3～5 张种子卡；5 会话验证。

**个人版完整产品（0.3.0，已落地）：** `install_personal` + `/kb-*` 投影 + `kb doctor` + 开场条 + `off/on` + `note`/`deposit-apply`/`todo`/`habit` + 分支感知 `import` + `logs/events.jsonl` + `kb report` / `technique bump`；日常入口 [`plugins/experience/PERSONAL-USE.md`](../../plugins/experience/PERSONAL-USE.md)；产品设计 [`docs/superpowers/specs/2026-11-20-personal-assistant-extreme-design.md`](../superpowers/specs/2026-11-20-personal-assistant-extreme-design.md)。

**不做：** 全项目清理；向量库；Fact 私有 git；自动发 marketplace；经验市场产品化；Cursor 自动命中对等（非个人版完成条件）。

| # | 指标 |
|---|---|
| 1 | 同仓两检出 personal 模式投影哈希一致 |
| 2 | 公开 clone：**零**业务 Fact |
| 3 | 5 会话中 ≥3 次命中/提示 Technique 且未要求关掉 |
| 4 | 「记一下」→ 可命中 ≤ 一次沉淀确认 |
| 5 | 陌生人只靠 plugin 安装跑通闭环 |
| 6 | 未过审条目不得进可分享层 |
| 7 | `kb doctor` 全绿；一周后 `kb report` 能看到 hit/note/deposit 计数 |

---

## 10. 实施顺序

1. 公开 `personal-kb` 去业务 + 引擎迁入 `plugins/experience`（合规一次）。  
2. 仅迁 aivoice → 本机 `facts/`；其它仓不动。  
3. 沉淀 skill + inbox + 命中 + 种子卡。  
4. 实机 5 会话验指标。  
5. 文档 / BACKLOG / 退役说明；按需扩仓与 plans 巡检渐进。

**实施时可选（不影响架构）：** 历史清理用新裸仓或 filter-repo；Playbook 作推荐依赖或文档第二行 install。

---

## 11. 关键不变量（改前必读）

1. 公开仓无业务 Fact。  
2. 确认 ≠ 真理；可分享需强度 + 去语境。  
3. 已跟踪文件不覆盖；team-tracked 用加性注入。  
4. plans 先分 exec/reference，禁止默认删 reference。  
5. 消费侧装一个 plugin，不跑三仓。  
6. 机器提案，人裁决可分享写入。
