---
description: 【经验库】个人版安装体检（hooks / commands 投影 / 日志）；不修改配置，只报告。
---

# /kb-doctor

【经验库】个人版安装体检（hooks / commands 投影 / 日志）；不修改配置，只报告。

## 怎么做

1. 解析引擎路径（同 `/kb-note`）。
2. 执行：`python3 <kb> doctor [--json]`。
3. 若 `NEEDS_FIX`，提示用户运行：`bash <plugin_root>/scripts/install_personal.sh`。
