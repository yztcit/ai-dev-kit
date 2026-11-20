# Cursor 适配（experience 0.3+）

**定位：** 薄适配。写入口仍是本机 `kb` CLI；Cursor 侧主要是 **`/kb-*` 命令投影**。

## 安装

```bash
bash plugins/experience/scripts/install_personal.sh
```

会把 `plugins/experience/commands/kb-*.md` 软链到 `~/.cursor/commands/`（与 Claude 同源正文）。

## 有什么 / 没有什么

| 能力 | Cursor |
|---|---|
| `/kb-note` · `/kb-deposit` · `/kb-habit` 等 | ✅ 投影后可用 |
| `/kb-ls` · `/kb-show` 只读浏览 | ✅ |
| SessionStart 开场条、技巧命中、Fact 自动 sync | ❌ 无 Claude 对等 hooks（本仓库不承诺对等） |
| `kb off` / `kb on` | ✅ CLI；主要影响 Claude hooks 段 |
| 日常入口 | [`plugins/experience/PERSONAL-USE.md`](../../plugins/experience/PERSONAL-USE.md) |

## 推荐用法

- 用 `/kb-*` 触发与 Claude 相同的 `python3 …/engine/kb …` 流程。  
- 看不见 `[experience]` 开场行是预期：改用 `/kb-status` / `/kb-report`，或看 `~/.local/share/dev-memory/logs/events.jsonl`。  
- 浏览落盘：`/kb-ls habit`、`/kb-show technique <id>` 等，不必翻 `dev-memory` 目录。  
- 需要自动投影/命中时，在 Claude Code 开会话，或手动 `kb sync <检出>`。  
- 健康检查：`python3 plugins/experience/engine/kb doctor`。
