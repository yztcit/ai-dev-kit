#!/bin/bash
# 流水线 A 自动巡检：每周跑一次，产出例外队列，有例外则弹 macOS 通知。
# 由 launchd 调度（com.tal.claude.skillhealth），也可手动执行。
# 脚本自定位到本仓库 health/ 目录，报告写进 sibling report/（gitignore 掉）。
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
SCAN="$SCRIPT_DIR/scan_skill_usage.py"
REPORT_DIR="$SCRIPT_DIR/report"
REPORT="$REPORT_DIR/skill-health-report.txt"
DAYS=90
COLD_DAYS=30

mkdir -p "$REPORT_DIR"

output=$(python3 "$SCAN" --days "$DAYS" --cold-days "$COLD_DAYS" --exceptions-only 2>&1)

{
  echo "=== $(date '+%Y-%m-%d %H:%M') 例外队列 ==="
  echo "$output"
  echo ""
} >> "$REPORT"

# 有例外（输出里含标记）则通知；「无例外。」或「最近 N 天内无」则静默
if echo "$output" | grep -qE '冷门|高重试'; then
  summary=$(echo "$output" | grep -E '冷门|高重试' | head -5 | tr '\n' ' ')
  osascript -e "display notification \"${summary}\" with title \"Skill 健康巡检：需裁决\""
fi
