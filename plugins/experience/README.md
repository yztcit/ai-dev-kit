# experience 插件

`experience` 是 AI-dev-kit 的经验复利插件：用于承载本机 `Fact`、`Technique` 和沉淀相关能力，但插件包本身不包含业务内容。

## 安装

在 AI-dev-kit 的插件市场中安装：

```bash
/plugin install experience@ai-dev-kit
```

安装后会注册：

- `SessionStart` → `hooks/session_start.sh`：同步本机 Fact、未接入提示、个人技巧数量等  
- `UserPromptSubmit` → `hooks/prompt_hit.sh`：按用户话术触发词匹配 `methods-personal` / 公开技巧，并注入 `[experience-technique]` 路径（须 Read 后执行；勿只引用项目 MEMORY）

本机若未走 plugin 安装、只改了 `~/.claude/settings.json`，也需同时挂上上述两条。

插件内 `techniques/` 只保留可分享公开索引；seed 在 `seed_techniques/`，首次复制到本机 `methods-personal/`。

## MEMORY_ROOT

默认运行时根目录为：

```text
~/.local/share/dev-memory
```

可通过环境变量 `DEV_MEMORY_ROOT` 覆盖。

首次使用时，运行时会按需创建以下目录和文件：

- `facts/`
- `methods-personal/`
- `scratch/`
- `inbox/facts/`
- `inbox/methods/`
- `index.json`

如果需要覆盖默认根目录，设置 `DEV_MEMORY_ROOT` 即可。
