#!/bin/bash
# 体系状态一览：自检 + 待处理队列。
#
# 用法: health [-v]
#   无参  概览（一行一项）
#   -v    展开明细
# 退出码: 0 = 无异常；1 = 有需要关注的东西（可接 shell 提示 / CI）
#
# 为什么要有它: 此前查状态要记三条命令、三个路径，还得问 Claude——
# 「要问才知道」本身就是缺口。这里给一个入口。
set -uo pipefail

REPO="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
SCRIPTS="$HOME/.claude/scripts"
REPORT="$REPO/health/report/skill-health-report.txt"
BACKLOG="$REPO/health/BACKLOG.md"
VERBOSE=0
[ "${1:-}" = "-v" ] && VERBOSE=1
rc=0

echo "── 体系自检 ──"

if launchctl list 2>/dev/null | grep -q com.tal.claude.skillhealth; then
  echo "  ✓ 定时巡检已加载（周一 09:15）"
else
  echo "  ✗ 定时巡检未加载 → 跑 $REPO/install.sh"; rc=1
fi

missing=""
for f in scan_skill_usage.py scan_capability_layers.py decision_log.py; do
  [ -e "$SCRIPTS/$f" ] || missing="$missing $f"
done
[ -e "$HOME/.claude/rules/conventions.md" ] || missing="$missing conventions.md"
if [ -z "$missing" ]; then
  echo "  ✓ 软链完整"
else
  echo "  ✗ 软链缺失:$missing → 跑 $REPO/install.sh"; rc=1
fi

if [ -f "$REPORT" ]; then
  echo "  ✓ 最近巡检：$(grep -oE '^=== [0-9-]+ [0-9:]+' "$REPORT" | tail -1 | cut -c5-)"
else
  echo "  ✗ 无巡检报告 → 跑 $SCRIPTS/skill-health-check.sh"; rc=1
fi

echo ""
echo "── 待处理 ──"

exc="$(python3 "$SCRIPTS/scan_skill_usage.py" --exceptions-only 2>&1)"
if printf '%s' "$exc" | grep -qE '^[0-9]+ 个待裁决'; then
  echo "  ⚠ 例外队列：$(printf '%s' "$exc" | grep -E '^[0-9]+ 个待裁决' | head -1)"; rc=1
  [ "$VERBOSE" = 1 ] && printf '%s\n' "$exc" | sed 's/^/    /'
else
  echo "  ✓ 例外队列：无"
fi

due="$(python3 "$SCRIPTS/decision_log.py" due 2>&1)"
if printf '%s' "$due" | grep -q '需重新审视'; then
  echo "  ⚠ 待复查裁决（ttl 到期）："; printf '%s\n' "$due" | sed 's/^/    /'; rc=1
else
  echo "  ✓ 待复查裁决：无"
fi

n="$(grep -cE '^## [0-9]+\.' "$BACKLOG" 2>/dev/null || echo 0)"
echo "  · 未接入项：$n 项"
if [ "$VERBOSE" = 1 ]; then
  grep -E '^## [0-9]+\.' "$BACKLOG" | sed 's/^/    /'
else
  echo "    （-v 展开；或看 $BACKLOG）"
fi

exit $rc
