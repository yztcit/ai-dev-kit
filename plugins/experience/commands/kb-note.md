---
description: 【经验库】先存草稿到本机 scratch；不改项目配置、不建技巧/待办。
---

# /kb-note

【经验库】先存草稿到本机 scratch；不改项目配置、不建技巧/待办。

## 怎么做

1. 解析引擎：`$HOME/workspace/AI-dev-kit/plugins/experience/engine/kb`；或 `EXPERIENCE_PLUGIN_ROOT/engine/kb`；或 `PERSONAL_INSTALL.json` 里的 `plugin_root`。
2. 执行：`python3 <kb> note --slug <短名> --body-file <路径>` 或 `--body "…"`。
3. 以 CLI 输出为准；不要在本文件外重复实现落盘逻辑。
