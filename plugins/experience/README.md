# experience 插件

`experience` 是 AI-dev-kit 的经验复利插件：用于承载本机 `Fact`、`Technique` 和沉淀相关能力，但插件包本身不包含业务内容。

## 安装

在 AI-dev-kit 的插件市场中安装：

```bash
/plugin install experience@ai-dev-kit
```

安装后会自动注册 `SessionStart` hook，实际执行脚本为 `hooks/session_start.sh`。
这个 hook 会先同步当前检出到本机 dev-memory，再按需输出未接入提示、`team-tracked` 个人事实提示和个人技巧卡数量。
插件内 `techniques/` 目录只保留可分享的公开技巧索引；内置 seed 会从 `seed_techniques/` 首次复制到本机 `methods-personal/`，不会直接作为公开技巧包暴露。

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
