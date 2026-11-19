# experience 插件

`experience` 是 AI-dev-kit 的经验复利插件：用于承载本机 `Fact`、`Technique` 和沉淀相关能力，但插件包本身不包含业务内容。

## 安装

在 AI-dev-kit 的插件市场中安装：

```bash
/plugin install experience@ai-dev-kit
```

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
