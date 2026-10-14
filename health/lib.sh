#!/bin/bash
# 巡检共享层：巡检参数 + 摘要判定的唯一来源，由 status.sh 与 skill-health-check.sh 共同 source。
#
# 为什么要有它：两个入口都要回答同一件事——「有没有需要人管的东西」。这段判定此前两处各写一份，
# 于是只修了一处：status.sh 拿 brief 的判定式去 grep --exceptions-only 的**正文**，而正文首行是
# 表头、根本没有那行，例外队列恒报「无」——通知弹了，health 却说没有待办。
# 判定只留一份，这类漂移才不可能再发生。
#
# 两个配置不变量（改了会静默失效，别乱调）：
#   1. COLD_DAYS 必须严格小于转录保留期（Claude Code cleanupPeriodDays，默认 30 天）——
#      等于或超过时，资产在够冷之前记录先被清理，冷门永远判不出来，报告会一直显示「无例外」。
#   2. DAYS 取保留期本身即可；取更大值拿不到更早的数据，只会把窗口写大，让「无数据」显得像「无例外」。

HEALTH_DAYS=30
HEALTH_COLD_DAYS=14

# 摘要文本 → 该走哪条处理路径，回显优先级最高的一档（无则空串）：待裁决 > 晋升候选 > 退出窗口。
# 入参是 brief（一行摘要，由 --brief-file 产出），不是扫描正文——正文里没有这些行。
#
# 判定必须匹配**数量前缀**（`^N 个…`），不能只匹配「待裁决」「晋升候选」「退出窗口」这几个词：
# 摘要里「**无**待裁决；N 个退出窗口」同样含这些词，只匹配词会让队列为空时照样判成有例外（实测踩过）。
health_brief_level() {
  local brief="${1:-}"
  if printf '%s' "$brief" | grep -qE '^[0-9]+ 个待裁决'; then
    echo "待裁决"
  elif printf '%s' "$brief" | grep -qE '^[0-9]+ 个晋升候选'; then
    echo "晋升候选"
  elif printf '%s' "$brief" | grep -qE '[0-9]+ 个退出窗口'; then
    echo "退出窗口"
  fi
}
