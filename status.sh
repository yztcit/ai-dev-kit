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

# 巡检参数与摘要判定来自 health/lib.sh，与定时巡检共用同一份——判定写两遍就会漂移，
# 之前正是这样：一边 grep 摘要、一边 grep 正文，本命令因此恒报「无例外」。
source "$REPO/health/lib.sh"

echo "── 体系自检 ──"

# 分三态判定：已加载 / 未加载 / 查不了。不能把「查不了」报成「未加载」——
# 受限会话下 launchctl 查询会静默失败，报成未加载等于假警报，把人赶去重跑安装脚本。
LABEL=com.tal.claude.skillhealth
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
if ! launchctl print "gui/$(id -u)" >/dev/null 2>&1; then
  echo "  · 定时巡检：查不到 launchd（非登录会话或受限环境），本次跳过判定"
elif launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then
  echo "  ✓ 定时巡检已加载（周一 09:15）"
elif [ -f "$PLIST" ]; then
  echo "  ✗ 定时巡检已安装但未加载 → launchctl load $PLIST"; rc=1
else
  echo "  ✗ 定时巡检未安装 → 跑 $REPO/install.sh"; rc=1
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

# 判定取 --brief-file 的**摘要**，不能 grep --exceptions-only 的正文：正文首行是表头，
# 「N 个待裁决」这行只在摘要里，grep 正文恒不匹配 → 例外队列恒报「无」。
# 摘要与正文出自同一次扫描（--brief-file 不抑制正文），不重跑、不重复落快照。
#
# 此处刻意不传 --snapshot：写快照是定时巡检的职责，本命令只读，重跑会让时间序列失真。
# 代价是这里看不到「退出窗口」（它靠对比上一轮快照得出），该信号由每周通知负责。
usage_brief_file="$(mktemp)"
exc="$(python3 "$SCRIPTS/scan_skill_usage.py" \
         --days "$HEALTH_DAYS" --cold-days "$HEALTH_COLD_DAYS" \
         --exceptions-only --brief-file "$usage_brief_file" 2>&1)"
usage_brief="$(cat "$usage_brief_file" 2>/dev/null)"
rm -f "$usage_brief_file"
if [ -n "$(health_brief_level "$usage_brief")" ]; then
  echo "  ⚠ 例外队列：$usage_brief"; rc=1
  [ "$VERBOSE" = 1 ] && printf '%s\n' "$exc" | sed 's/^/    /'
else
  echo "  ✓ 例外队列：$usage_brief"
fi

# 晋升候选同样会弹通知（优先级次于例外），本命令不报就会重演「通知弹了 health 说没有」
layers_brief_file="$(mktemp)"
layers="$(python3 "$SCRIPTS/scan_capability_layers.py" --brief-file "$layers_brief_file" 2>&1)"
layers_brief="$(cat "$layers_brief_file" 2>/dev/null)"
rm -f "$layers_brief_file"
if [ "$(health_brief_level "$layers_brief")" = "晋升候选" ]; then
  echo "  ⚠ 晋升候选：$layers_brief"; rc=1
  [ "$VERBOSE" = 1 ] && printf '%s\n' "$layers" | sed 's/^/    /'
else
  echo "  ✓ 晋升候选：无"
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
