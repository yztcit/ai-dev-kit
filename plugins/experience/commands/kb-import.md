---
description: 【经验库】把当前检出 `.claude` 收成 KB（主分支进 base，功能分支进覆盖层）；不删仓库工作区文件。
---

# /kb-import

【经验库】把当前检出 `.claude` 收成 KB（主分支进 base，功能分支进覆盖层）；不删仓库工作区文件。

## 怎么做

1. 解析引擎路径（同 `/kb-note`）。
2. 在目标检出根目录执行：`python3 <kb> import <检出路径> [--force]`。
3. 分支规则由引擎判定；以 CLI 输出与 events 为准。
