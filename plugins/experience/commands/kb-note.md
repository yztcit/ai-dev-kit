---
description: 【经验库】先存草稿到本机 scratch；不改项目配置、不建技巧/待办。别名：记一下 / 先记下来 / 做个草稿。
---

# /kb-note

【经验库】先存草稿到本机 scratch；不改项目配置、不建技巧/待办。

用户说「记一下」「先记下来」「先存一下」「做个草稿」且未用斜杠时，按本命令执行（与 skill 剧本同源，斜杠入口只认 command）。

## 怎么做

1. 解析引擎：`$HOME/workspace/AI-dev-kit/plugins/experience/engine/kb`；或 `EXPERIENCE_PLUGIN_ROOT/engine/kb`；或 `PERSONAL_INSTALL.json` 里的 `plugin_root`。
2. 需要完整步骤时可打开插件内 `skills/kb-note/SKILL.md`，但落盘只通过 CLI。
3. 执行：`python3 <kb> note --slug <短名> --body-file <路径>` 或 `--body "…"`。
4. 以 CLI 输出为准；不要在本文件外重复实现落盘逻辑。
