# Claude 适配（experience 0.3+）

**定位：** 个人版主路径。hooks + `/kb-*` 命令投影；写入口仍是本机 `kb` CLI。

## 安装

```bash
bash plugins/experience/scripts/install_personal.sh
```

会：投影 `commands/kb-*.md` → `~/.claude/commands/`；注册 `SessionStart` / `UserPromptSubmit`；**不**把 capture skills 链到 `~/.claude/skills`（避免 `/note` 与 `/kb-note` 双开）。

## 终端 Claude Code CLI

| 能力 | 状态 |
|---|---|
| `/kb-*` 斜杠 | ✅ |
| SessionStart 开场条可见 | ✅（system / hook 输出） |
| 技巧命中、Fact sync | ✅（`kb on` 时） |
| `/kb-ls` · `/kb-show` | ✅ |

推荐 CLI 路径（若 GUI/插件另配）：`/opt/homebrew/bin/claude`（以本机 `which claude` 为准）。

## Android Studio / JetBrains「CC GUI」等

| 能力 | 状态 |
|---|---|
| `/kb-*`（依赖已投影的 commands + 可用的 `claude` 二进制） | ✅ 配好 CLI 路径后可用 |
| 开场条 `[experience] …` 画在聊天里 | ⚠️ 常不可见；hooks 仍可能已跑 |
| 替代可见信号 | `/kb-status` · `/kb-report` · `events.jsonl` 的 `session_start` |
| `spawn Unknown system error -88` | 多为插件/SDK 截断二进制；把 Claude CLI 指到本机已签名的 `claude`，勿改 kb 内核 |

日常入口：[`plugins/experience/PERSONAL-USE.md`](../../plugins/experience/PERSONAL-USE.md)。
