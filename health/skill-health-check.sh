#!/bin/bash
# 流水线 A 自动巡检：每周跑一次，产出例外队列，有例外则弹 macOS 通知。
# 由 launchd 调度（com.tal.claude.skillhealth），也可手动执行。
# 脚本自定位到本仓库 health/ 目录，报告写进 sibling report/（gitignore 掉）。
#
# 巡检参数与摘要判定见 lib.sh（唯一来源，与 status.sh 共用）。
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
source "$SCRIPT_DIR/lib.sh"
SCAN="$SCRIPT_DIR/scan_skill_usage.py"
LAYERS="$SCRIPT_DIR/scan_capability_layers.py"
REPORT_DIR="$SCRIPT_DIR/report"
REPORT="$REPORT_DIR/skill-health-report.txt"
HISTORY="$REPORT_DIR/skill-usage-history.jsonl"
BRIEF="$REPORT_DIR/.brief"

mkdir -p "$REPORT_DIR"

# 摘要由脚本写文件，而不是在 shell 里 grep 表格——表格原文塞进通知只会变成噪声
# （连续空格 + 几十个破折号），且 shell 侧的格式化很脆。
# 传 --brief-file 与主扫描同一次运行，避免为拿摘要而重跑（重跑会让快照重复落盘）。
output=$(python3 "$SCAN" --days "$HEALTH_DAYS" --cold-days "$HEALTH_COLD_DAYS" \
           --exceptions-only --snapshot "$HISTORY" --brief-file "$BRIEF.usage" 2>&1)
usage_brief=$(cat "$BRIEF.usage" 2>/dev/null)

layers=$(python3 "$LAYERS" --brief-file "$BRIEF.layers" 2>&1)
layers_brief=$(cat "$BRIEF.layers" 2>/dev/null)

{
  echo "=== $(date '+%Y-%m-%d %H:%M') 巡检（用量侧 + 放置侧）==="
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
usage_level="$(health_brief_level "$usage_brief")"
layers_level="$(health_brief_level "$layers_brief")"
if [ "$usage_level" = "待裁决" ]; then
  notify "Skill 健康巡检：需裁决" "$usage_brief"
elif [ "$layers_level" = "晋升候选" ]; then
  notify "能力分层巡检：晋升候选" "$layers_brief"
elif [ "$usage_level" = "退出窗口" ]; then
  notify "Skill 健康巡检：资产退出窗口" "$usage_brief"
fi
