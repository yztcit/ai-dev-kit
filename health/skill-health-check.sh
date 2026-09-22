#!/bin/bash
# 流水线 A 自动巡检：每周跑一次，产出例外队列，有例外则弹 macOS 通知。
# 由 launchd 调度（com.tal.claude.skillhealth），也可手动执行。
# 脚本自定位到本仓库 health/ 目录，报告写进 sibling report/（gitignore 掉）。
#
# 两个配置不变量（改了会静默失效，别乱调）：
#   1. COLD_DAYS 必须 < 转录保留期（Claude Code cleanupPeriodDays，默认 30 天）。
#      等于或超过保留期时，资产在够冷之前记录就先被清理了，冷门永远判不出来，
#      报告会一直显示「无例外」——看起来健康，其实是没有数据。
#   2. DAYS 取保留期本身即可。取更大值不会拿到更早的数据（那部分已被清理），
#      只是把窗口写大，让「无数据」显得像「无例外」。
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
SCAN="$SCRIPT_DIR/scan_skill_usage.py"
LAYERS="$SCRIPT_DIR/scan_capability_layers.py"
REPORT_DIR="$SCRIPT_DIR/report"
REPORT="$REPORT_DIR/skill-health-report.txt"
HISTORY="$REPORT_DIR/skill-usage-history.jsonl"
BRIEF="$REPORT_DIR/.brief"
DAYS=30
COLD_DAYS=14

mkdir -p "$REPORT_DIR"

# 摘要由脚本写文件，而不是在 shell 里 grep 表格——表格原文塞进通知只会变成噪声
# （连续空格 + 几十个破折号），且 shell 侧的格式化很脆。
# 传 --brief-file 与主扫描同一次运行，避免为拿摘要而重跑（重跑会让快照重复落盘）。
output=$(python3 "$SCAN" --days "$DAYS" --cold-days "$COLD_DAYS" \
           --exceptions-only --snapshot "$HISTORY" --brief-file "$BRIEF.usage" 2>&1)
usage_brief=$(cat "$BRIEF.usage" 2>/dev/null)

layers=$(python3 "$LAYERS" --brief-file "$BRIEF.layers" 2>&1)
layers_brief=$(cat "$BRIEF.layers" 2>/dev/null)

{
  echo "=== $(date '+%Y-%m-%d %H:%M') 例外队列 ==="
  echo "$output"
  echo ""
  echo "$layers"
  echo ""
} >> "$REPORT"

# 通知：用 osascript。文案在源头已压成一行——通知横幅宽度有限，塞表格原文只会是噪声。
#
# 关于「点击通知」：`display notification` 不支持指定点击目标，点击行为由系统决定，
# 脚本侧控制不了。终端用户看到的「点一下跳到某个目录」即由此而来。
#
# 已尝试并否决的方案（别重复走）：terminal-notifier + `-open file://<报告>` 本可让
# 点击打开报告文件，但在 macOS 26 上它以「Notifications are not allowed for this
# application」直接失败（退出码 3），且不会出现在「系统设置 → 通知」列表里——
# 是系统级不允许，不是待授权。装了它反而会导致一条通知都弹不出来。
notify() {
  local title="$1" body="$2"
  [ -n "$body" ] || return 0
  local safe
  safe=$(printf '%s' "$body" | tr -d '"\\')
  osascript -e "display notification \"$safe\" with title \"$title\"" 2>/dev/null
  return 0
}

# 优先级：需裁决的例外 > 晋升候选 > 退出窗口；「无例外」「无数据」「无晋升候选」静默
#
# 判定必须匹配**数量前缀**（`^N 个…`），不能只匹配「待裁决」「晋升候选」「退出窗口」
# 这几个词——摘要里「**无**待裁决；N 个退出窗口」「**无**晋升候选」都含这些词，
# 只匹配词会让队列为空时照样弹通知（实测踩过：两个队列都空，通知照弹）。
if printf '%s' "$usage_brief" | grep -qE '^[0-9]+ 个待裁决'; then
  notify "Skill 健康巡检：需裁决" "$usage_brief"
elif printf '%s' "$layers_brief" | grep -qE '^[0-9]+ 个晋升候选'; then
  notify "能力分层巡检：晋升候选" "$layers_brief"
elif printf '%s' "$usage_brief" | grep -qE '[0-9]+ 个退出窗口'; then
  notify "Skill 健康巡检：资产退出窗口" "$usage_brief"
fi
