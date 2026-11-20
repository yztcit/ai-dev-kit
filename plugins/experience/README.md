# experience 插件

`experience` 是 AI-dev-kit 的经验复利插件：用于承载本机 `Fact`、`Technique` 和沉淀相关能力，但插件包本身不包含业务内容。

**个人版日常用法（0.3.0）：** 见 [`PERSONAL-USE.md`](./PERSONAL-USE.md)（唯一日常入口）。设计见 [`docs/superpowers/specs/2026-11-20-personal-assistant-extreme-design.md`](../../docs/superpowers/specs/2026-11-20-personal-assistant-extreme-design.md)。

## 安装（个人版推荐）

```bash
bash plugins/experience/scripts/install_personal.sh
python3 plugins/experience/engine/kb doctor
```

会：建本机 `dev-memory`（含 `todos/`、`habits/`、`state.json`）、拷种子技巧、软链 `note`/`deposit`、投影 `commands/kb-*.md` 到 `~/.claude/commands` 与 `~/.cursor/commands`、写入 Claude `SessionStart` + `UserPromptSubmit` hooks、写安装标记。

也可在 marketplace 安装：

```bash
/plugin install experience@ai-dev-kit
```

安装后 hooks：

- `SessionStart` → `hooks/session_start.sh`：`kb on` 时同步 Fact、打印开场条、未接入提示、写 `session_start` 事件；`kb off` 时短路  
- `UserPromptSubmit` → `hooks/prompt_hit.sh`：技巧命中注入 + 写 `technique_hit` 事件 / `hit_count`（off 时短路）

一键开关：`python3 engine/kb off` · `on`；或 `/kb-off` · `/kb-on`。

插件内 `techniques/` 只保留可分享公开索引；seed 在 `seed_techniques/`，首次复制到本机 `methods-personal/`。

## MEMORY_ROOT

默认运行时根目录为：

```text
~/.local/share/dev-memory
```

可通过环境变量 `DEV_MEMORY_ROOT` 覆盖。

首次使用时，运行时会按需创建以下目录和文件：

- `facts/`、`methods-personal/`、`scratch/`
- `todos/items.jsonl`、`habits/`、`state.json`
- `logs/events.jsonl`
- `inbox/facts/`、`inbox/methods/`、`index.json`

如果需要覆盖默认根目录，设置 `DEV_MEMORY_ROOT` 即可。
