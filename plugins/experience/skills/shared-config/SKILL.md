---
name: shared-config
description: 同一仓库多个检出/分支的 .claude 与 CLAUDE.md 怎么管——唯一权威在本机 ~/.local/share/dev-memory/facts，检出侧由 experience kb sync 渲染投影；用户说「配置对不上」「汇总/合并回主干」「新检出没配置」时用。旧的 sync.py 只作未登记仓库回退
---

# 同一仓库多个检出的配置

## 现在的模型

```
~/.local/share/dev-memory/facts/<host>/<group>/<repo>/
  base/                唯一可写处：CLAUDE.md、agents、rules、skills、tools
  branches/<branch>/   分支覆盖层：同路径整文件覆盖 base，仅该分支可见
```

引擎：`~/workspace/AI-dev-kit/plugins/experience/engine/kb`  
`personal-kb` 仓库已退役，不要再 clone / 依赖它。

检出里的 `.claude/` 和根目录 `CLAUDE.md` 是 `kb sync` 渲染出来的**投影**（`overlay: personal` 模式）。  
`team-tracked` 仓（团队已提交同名文件）不覆盖已跟踪路径，个人内容加性注入。

`SessionStart` 会跑 experience 的 `kb hook` / `session_start.sh`。

## 命令

```bash
KB=~/workspace/AI-dev-kit/plugins/experience/engine/kb
$KB sync [目录]            # 渲染（hook 已自动做）
$KB status [目录]          # 身份 / 分支 / 覆盖层 / overlay / 一致性
$KB check [--brief]        # 知识过期、覆盖层滞留
$KB verify <相对路径>      # 复核后标注 verified_at
$KB import <目录>          # 新仓库接入
$KB promote <相对路径> --from <分支>
```

## 用户说「汇总 / 合并回主干 / 完工了」

1. `$KB status <分支检出>` 看覆盖层有哪些文件  
2. 逐个对照**代码现实**判断是否进主干  
3. 该进：`$KB promote <相对路径> --from <分支>`  
4. 不该进：删 `branches/<分支>/` 下对应文件  
5. 各检出跑一次 `$KB sync`

## 不变量

- **不要直接改检出投影**（会被备份后覆盖）。改 `facts/.../base` 或覆盖层。  
- 覆盖层整文件覆盖，必须回收（promote 或删除）。  
- 含本机路径/凭证的 settings、以及 `plans/` 执行稿不进可分享层。  
- 已 git 跟踪的团队文件禁止投影覆盖。

## 未登记仓库

`kb hook` 未登记时回退 `AI-dev-kit/shared-config/sync.py`。要迁入：`$KB import <检出>`。
