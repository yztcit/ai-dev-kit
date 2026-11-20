# Cursor 适配（experience 0.3）

**定位：** 薄适配。写入口仍是本机 `kb` CLI；Cursor 侧主要是 **`/kb-*` 命令投影**。

## 安装

```bash
bash plugins/experience/scripts/install_personal.sh
```

会把 `plugins/experience/commands/kb-*.md` 软链到 `~/.cursor/commands/`（与 Claude 同源正文）。

## 有什么 / 没有什么

| 能力 | Cursor |
|---|---|
| `/kb-note` 等命令 | ✅ 投影后可用 |
| SessionStart 开场条、技巧命中、Fact 同步 | ❌ 无官方等价 hooks（本仓库不承诺对等） |
| `kb off` / `kb on` | ✅ CLI；仅影响 Claude hooks 注册段 |
| 日常入口 | [`plugins/experience/PERSONAL-USE.md`](../../plugins/experience/PERSONAL-USE.md) |

## 推荐用法

- 在 Cursor 里用 `/kb-*` 触发与 Claude 相同的 `python3 …/engine/kb …` 说明。  
- 需要自动投影/命中时，在 Claude Code 开会话，或手动 `kb sync <检出>`。  
- 健康检查：`python3 plugins/experience/engine/kb doctor`（命令文件缺失为 warn，非致命）。