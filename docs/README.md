# 文档管理（统一入口）

本仓库**所有设计/计划/适配说明**以 `docs/` 为唯一现行树。根目录只保留「宪法级」短入口（如 `DESIGN.md`）与指向此处的 stub。

## 目录

```text
docs/
  README.md                 ← 本文件：索引 + 生命周期
  design/                   ← 长期原理（可跨多个实现版本）
    EXPERIENCE-COMPOUNDING.md
  superpowers/
    specs/                  ← 产品/功能设计定稿（现行）
    plans/                  ← 实现计划（现行，配对 specs）
    archive/
      specs/                ← 已取代的设计
      plans/                ← 已完成/已取代的计划
  adapters/                 ← 各 AI 工具薄适配说明
```

| 角色 | 现行位置 | 日常入口 |
|---|---|---|
| 三层体系不变量 | 根 `DESIGN.md` | 改体系前必读 |
| 经验复利原理 | `docs/design/EXPERIENCE-COMPOUNDING.md` | 与 0.3 产品对齐 |
| 个人助手 0.3 设计 | `docs/superpowers/specs/2026-11-20-…` | 已批准并落地 |
| 个人助手 0.3 计划 | `docs/superpowers/plans/2026-11-20-…` | 已执行完，可归档 |
| 用法 | `plugins/experience/PERSONAL-USE.md` | **用户只看这个** |

## 配套关系（spec ↔ plan）

- 每份 **plan** 必须在文首写 `**Spec:** <path>`。  
- 每份 **spec** 必须写状态：`草案 | 已批准 | 已落地 | 已取代`，并链到对应 plan。  
- **原理文**（`docs/design/*`）不替代 spec：原理稳定少改；版本化产品决策进 `specs/`。

## 生命周期与清理

| 状态 | 放哪 | 何时清理/搬迁 |
|---|---|---|
| **现行** | `specs/` 或 `plans/` | 正在用或刚落地 ≤1 个大版本 |
| **已落地且有更新版** | plan → `archive/plans/`；旧 spec → `archive/specs/` | 新版合并进 main 后的同一 PR 或紧随的 docs PR |
| **已取代** | `archive/`，文首加「勿再执行/勿再当权威」 | 同上；**不删文件**（git 历史即可追），避免断链 |
| **过期可删** | 仅当：① 已在 archive ≥90 天，② 无外链依赖，③ 内容已完全并入现行文档 | 删前在本 README「变更记录」记一笔 |

**禁止：**

- 在仓库根再建 `plans/`，或在 `docs/` 外另开实现计划目录。  
- 留下「现行」与「过期」两份都可执行的 plan（必须 archive + 文首作废）。  
- 用过期 plan 当任务源开新实施。

**建议节奏：** 每个大版本收尾时扫一次 `docs/superpowers/{plans,specs}`，把已取代项挪进 `archive/`，并更新本页索引表。

## 现行索引

| 文档 | 状态 |
|---|---|
| [design/EXPERIENCE-COMPOUNDING.md](./design/EXPERIENCE-COMPOUNDING.md) | 原理 · 有效（0.3 已对齐） |
| [superpowers/specs/2026-11-20-personal-assistant-extreme-design.md](./superpowers/specs/2026-11-20-personal-assistant-extreme-design.md) | 已落地 |
| [superpowers/plans/2026-11-20-experience-personal-0.3.md](./superpowers/plans/2026-11-20-experience-personal-0.3.md) | 已执行完（可下次收尾时 archive） |
| [superpowers/archive/plans/2026-11-19-experience-compounding.md](./superpowers/archive/plans/2026-11-19-experience-compounding.md) | 已取代 · 勿执行 |
| [adapters/cursor.md](./adapters/cursor.md) | 有效 |
| [adapters/claude_plugins.md](./adapters/claude_plugins.md) | 有效 |

## 变更记录

- 2026-11-20：统一迁入 `docs/`；根目录 `plans/` **已删除**（勿再建）；V1 plan 进 archive；本机制生效。
