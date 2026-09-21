# ai-dev-kit

跨项目通用的 Claude Code 能力沉淀仓库。这里的每个 plugin 都**不含任何业务/团队语境**，任何项目、任何团队装上就能用。

## 分层定位

| 层 | 仓库 | 特征 |
|---|---|---|
| 公共通用（本仓库） | `yztcit/ai-dev-kit` | 不含业务、不含团队语境，哪里都能用 |
| 团队共用 | `yztcit/claude_plugins`（marketplace `tal-tools`） | TAL 团队约定、内部工具 |
| 项目业务 | 各项目 `.claude/` | 绑死本项目（如 ai_eyes / xpy_interact） |

依赖单向：`项目业务 → 团队共用 → 公共通用`，禁止反向引用。

## 晋升规则

能力从下层晋升到本仓库前，必须通过**去语境化**检查：

> 残留某个项目/团队的影子（具体机型、业务术语、写死的路径、内部服务名），就还没资格进本仓库。

判据就一条：把插件放到一个完全陌生的项目里，它能否不依赖任何额外约定直接生效。

## video/：视频生成请求整理

`plugins/video` 提供跨项目通用的视频提示词整理能力，不含具体模型/产品语境。

| 组件 | 类型 | 说明 | 调用方式 |
|---|---|---|---|
| `video-pe` | Skill | 把文字与图/视频/音频素材引用整理成结构化视频生成请求（只格式化，不扩写剧情） | `/video:video-pe` |

## health/：skill 健康巡检工具（流水线 A）

`health/` 是一套跨项目通用的 skill 健康巡检工具，通过解析本地会话转录（`~/.claude/projects/<项目>/*.jsonl`）算出每个 skill 的冷门度/调用次数/重试率，产出「例外队列」供人裁决，替代人工例行巡检。

- `scan_skill_usage.py` — 转录解析，产出调用统计 + 例外队列
- `decision_log.py` — 决策日志（双向 override + ttl 重入队列）
- `skill-health-check.sh` — 巡检入口，有例外弹 macOS 通知
- `install.sh` — 幂等安装器，软链脚本 + 注册 launchd 定时任务（周一 09:15）

换设备安装：`clone` 本仓库后 `./health/install.sh`。

## 当前状态

- `plugins/video` 已落地：`video-pe` 视频生成请求整理。
- `health/` 已落地（流水线 A），报告与决策日志写入 `health/report/`（gitignore，本地可见）。
