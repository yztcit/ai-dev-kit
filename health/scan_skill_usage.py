#!/usr/bin/env python3
"""流水线 A：转录解析脚本（零埋点）。

从 ~/.claude/projects/<项目>/*.jsonl 的真实会话转录中，提取 Skill 调用的
tool_use 事件，聚合出按 skill 的健康信号：调用次数 / 最近使用 / 冷门度 / 重试率。

用法:
    python3 scan_skill_usage.py [--days 30] [--retry-window-sec 600] [--json]

数据来源（v4 实测确认）:
    ~/.claude/projects/<项目>/*.jsonl
    每行一条 JSON，Skill 调用位于 message.content[] 中:
        {type:"tool_use", name:"Skill", input:{skill:"<名>", args:"..."}}
    行级带 timestamp(ISO8601)、sessionId。
"""
import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

PROJECTS_DIR = os.path.expanduser("~/.claude/projects")


def parse_ts(s: str) -> datetime:
    # 兼容 "2026-08-12T11:59:11.639Z" 与无小数秒
    s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def canonical_skill(raw: str) -> str:
    """规范化 skill 名。

    转录里同一 skill 有两种记法：裸名（如 `frontend-design`）和插件前缀名
    （如 `frontend-design:frontend-design`、`dev:solution-design`）。取冒号后
    最后一段作为 skill 名，把两种记法归并为同一身份，避免冷门度被拆散误判。
    """
    return raw.rsplit(":", 1)[-1]


def iter_skill_events():
    """遍历所有项目转录，产出 (sessionId, timestamp, canonical_skill) 三元组。"""
    if not os.path.isdir(PROJECTS_DIR):
        return
    for proj in os.listdir(PROJECTS_DIR):
        proj_dir = os.path.join(PROJECTS_DIR, proj)
        if not os.path.isdir(proj_dir):
            continue
        for fn in os.listdir(proj_dir):
            if not fn.endswith(".jsonl"):
                continue
            path = os.path.join(proj_dir, fn)
            try:
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if obj.get("type") != "assistant":
                            continue
                        for c in obj.get("message", {}).get("content", []):
                            if not isinstance(c, dict):
                                continue
                            if c.get("type") != "tool_use" or c.get("name") != "Skill":
                                continue
                            skill = c.get("input", {}).get("skill")
                            ts = obj.get("timestamp")
                            sid = obj.get("sessionId", "")
                            if skill and ts:
                                yield sid, parse_ts(ts), canonical_skill(skill)
            except OSError:
                continue


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30, help="只统计最近 N 天内的调用")
    ap.add_argument("--retry-window-sec", type=int, default=600,
                    help="同一 skill 在此窗口内再次调用记为一次重试")
    ap.add_argument("--json", action="store_true", help="输出 JSON 而非表格")
    ap.add_argument("--cold-days", type=int, default=30,
                    help="最近 N 天未用视为冷门，进例外队列")
    ap.add_argument("--exceptions-only", action="store_true",
                    help="只输出例外队列（冷门 + 高重试），不输出全量表")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=args.days)

    # skill -> {count, last_ts, sessions:set, retries:int, events:[(ts,sid)]}
    agg = defaultdict(lambda: {"count": 0, "last_ts": None,
                               "sessions": set(), "events": []})

    for sid, ts, skill in iter_skill_events():
        if ts < cutoff:
            continue
        a = agg[skill]
        a["count"] += 1
        a["sessions"].add(sid)
        a["events"].append(ts)
        if a["last_ts"] is None or ts > a["last_ts"]:
            a["last_ts"] = ts

    # 重试：同一 skill 在 retry_window_sec 内再次调用
    for skill, a in agg.items():
        events = sorted(a["events"])
        retries = 0
        for i in range(1, len(events)):
            if (events[i] - events[i - 1]).total_seconds() <= args.retry_window_sec:
                retries += 1
        a["retries"] = retries
        a["last_days_ago"] = (now - a["last_ts"]).days if a["last_ts"] else None
        del a["events"]

    # 排序：冷门度优先（最久未用在前）
    rows = sorted(agg.items(), key=lambda kv: kv[1]["last_days_ago"] or 0, reverse=True)

    # 例外队列：冷门（最近 cold_days 未用）或 高重试（重试 >= 2 且调用少）
    def is_cold(a):
        return a["last_days_ago"] is not None and a["last_days_ago"] >= args.cold_days

    def is_flaky(a):
        return a["retries"] >= 2 and a["count"] < 5

    exceptions = [(s, a) for s, a in rows if is_cold(a) or is_flaky(a)]

    if args.exceptions_only:
        if not exceptions:
            print("无例外。")
            return
        print(f"例外队列（冷门≥{args.cold_days}天 或 高重试）：\n")
        print(f"{'skill':<24} {'调用':>4} {'会话':>4} {'重试':>4} {'最近(天前)':>10}  {'标记'}")
        print("-" * 68)
        for skill, a in exceptions:
            tags = []
            if is_cold(a):
                tags.append("冷门")
            if is_flaky(a):
                tags.append("高重试")
            print(f"{skill:<24} {a['count']:>4} {len(a['sessions']):>4} "
                  f"{a['retries']:>4} {a['last_days_ago']:>10}  {','.join(tags)}")
        return

    if args.json:
        out = {skill: {"count": a["count"], "sessions": len(a["sessions"]),
                       "retries": a["retries"],
                       "last_days_ago": a["last_days_ago"]}
               for skill, a in rows}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    if not rows:
        print(f"最近 {args.days} 天内无 Skill 调用记录。")
        return

    print(f"最近 {args.days} 天内的 Skill 调用统计（重试窗口 {args.retry_window_sec}s）\n")
    print(f"{'skill':<24} {'调用':>4} {'会话':>4} {'重试':>4} {'最近(天前)':>10}")
    print("-" * 52)
    for skill, a in rows:
        print(f"{skill:<24} {a['count']:>4} {len(a['sessions']):>4} "
              f"{a['retries']:>4} {a['last_days_ago']:>10}")

    if exceptions:
        print(f"\n⚠️ 例外队列（需人裁决）：{len(exceptions)} 个")
        for skill, a in exceptions:
            tags = []
            if is_cold(a):
                tags.append("冷门")
            if is_flaky(a):
                tags.append("高重试")
            print(f"  - {skill}（{','.join(tags)}）")


if __name__ == "__main__":
    main()
