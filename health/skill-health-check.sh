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
REPORT_DIR="$SCRIPT_DIR/report"
REPORT="$REPORT_DIR/skill-health-report.txt"
HISTORY="$REPORT_DIR/skill-usage-history.jsonl"
DAYS=30
COLD_DAYS=14

mkdir -p "$REPORT_DIR"

# --snapshot 落 append-only 聚合，使时间序列不随源转录过期而丢失
output=$(python3 "$SCAN" --days "$DAYS" --cold-days "$COLD_DAYS" \
           --exceptions-only --snapshot "$HISTORY" 2>&1)

{
  echo "=== $(date '+%Y-%m-%d %H:%M') 例外队列 ==="
  echo "$output"
  echo ""
} >> "$REPORT"

# 有例外（冷门/高重试/高失败）或资产退出窗口则通知；「无例外」「无数据」按需静默
if echo "$output" | grep -qE '冷门|高重试|高失败'; then
  summary=$(echo "$output" | grep -E '冷门|高重试|高失败' | head -5 | tr '\n' ' ')
  osascript -e "display notification \"${summary}\" with title \"Skill 健康巡检：需裁决\""
elif echo "$output" | grep -q '退出窗口'; then
  summary=$(echo "$output" | grep '退出窗口' | head -3 | tr '\n' ' ')
  osascript -e "display notification \"${summary}\" with title \"Skill 健康巡检：资产退出窗口\""
fi
