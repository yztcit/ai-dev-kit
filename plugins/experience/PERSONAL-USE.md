# 个人版日常用法（完整产品）

版本：与 `memory_paths.PRODUCT_VERSION` 对齐（当前 0.2.0）  
目标：日常只**用**，不边用边补流程。反馈靠本机日志，不靠记忆。

## 一次安装（本机）

```bash
bash ~/workspace/AI-dev-kit/plugins/experience/scripts/install_personal.sh
python3 ~/workspace/AI-dev-kit/plugins/experience/engine/kb doctor
```

`doctor` 全绿即可。换机器或挪了 `AI-dev-kit` 目录后重跑 install。

## 日常三句话

| 你说 | 系统做什么 |
|---|---|
| （正常写代码） | SessionStart 同步 Fact；话术命中技巧卡并写入 `logs/events.jsonl` |
| 「记一下」 | 写入 `scratch/`，并应打点 `kb event note` |
| 「沉淀」 | 拆 Fact / Technique / plans，确认后落盘，并打点 `kb event deposit` |

技巧真有用、要升强度：

```bash
python3 .../engine/kb technique bump investigate-before-conclude
# 或 --to repeated / contradicted
```

## 反馈数据在哪

```text
~/.local/share/dev-memory/logs/events.jsonl
```

汇总：

```bash
python3 ~/workspace/AI-dev-kit/plugins/experience/engine/kb report --days 30
```

事件类型：`session_start` · `technique_hit` · `note` · `deposit` · `technique_bump`

## 新仓库要项目 Fact 时

未接入会在开场提示。按需：

```bash
python3 .../engine/kb import "<检出路径>"
```

不 import 也能用「记一下 / 沉淀 / 技巧命中」——只是没有该仓 Fact。

## 出问题先跑

```bash
python3 .../engine/kb doctor
bash .../scripts/install_personal.sh
```

## 明确不做（避免日常又补流程）

- 不在日常中改 hook 形态 / 平台叙事
- 不做向量检索、跨设备 Fact 同步、对外收费
- Cursor 自动命中**不是**个人版完成条件（Claude Code 是）
