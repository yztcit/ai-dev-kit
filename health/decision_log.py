#!/usr/bin/env python3
"""决策日志：人看数据做裁决，双向可 override，形成闭环。

决策日志是一份 JSONL（默认写到本仓库 health/report/skill-decisions.jsonl，
已 gitignore，不随仓库共享），每条一条裁决。自动化只 flag（建议），动作由人做，
但必须带理由 + 时效。

schema（每条一条 JSON）:
{
  "skill": "gen-commit",          # 哪个 skill/agent
  "action": "keep" | "retire",     # 裁决方向
  "override": false,               # 是否 override 评测结论
  "reason": "特殊场景需暂留",       # 为什么
  "scenario_tag": "xx机型兼容",    # 可选，override keep 时的场景标签
  "ttl": "2026-10-01",            # 可选，keep 的重新审视日期，到期重入队列
  "decided_at": "2026-09-03T...", # 记录时间
  "by": "chenping26"               # 谁做的裁决
}

用法:
    python3 decision_log.py record --skill gen-commit --action keep --reason "..." [--scenario-tag ...] [--ttl 2026-10-01]
    python3 decision_log.py list [--skill xxx]
    python3 decision_log.py due     # 列出 ttl 到期、需重新审视的 keep 决策
"""
import argparse
import json
import os
from datetime import datetime, date, timezone

# 自定位到本脚本所在目录（health/），决策日志写进 sibling report/，gitignore 掉。
_REPO_HEALTH_DIR = os.path.dirname(os.path.realpath(__file__))
REPORT_DIR = os.path.join(_REPO_HEALTH_DIR, "report")
LOG_PATH = os.path.join(REPORT_DIR, "skill-decisions.jsonl")
DEFAULT_BY = os.environ.get("USER", "unknown")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load():
    if not os.path.exists(LOG_PATH):
        return []
    rows = []
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def record(args):
    os.makedirs(REPORT_DIR, exist_ok=True)
    rec = {
        "skill": args.skill,
        "action": args.action,
        "override": args.override,
        "reason": args.reason,
        "scenario_tag": args.scenario_tag,
        "ttl": args.ttl,
        "decided_at": _now(),
        "by": args.by,
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"已记录裁决：{rec['skill']} -> {rec['action']} (override={rec['override']})")


def list_(args):
    rows = _load()
    if args.skill:
        rows = [r for r in rows if r["skill"] == args.skill]
    if not rows:
        print("无决策记录。")
        return
    print(f"{'skill':<22} {'action':<7} {'override':<9} {'ttl':<12} {'by':<12} reason")
    print("-" * 80)
    for r in rows:
        ttl = r.get("ttl") or "-"
        print(f"{r['skill']:<22} {r['action']:<7} {str(r['override']):<9} "
              f"{ttl:<12} {r.get('by','') or '-':<12} {r.get('reason','')}")


def due(args):
    """列出 keep 且 ttl 已到期的决策，这些需要重新审视（重入例外队列）。"""
    today = date.today()
    rows = _load()
    due_rows = []
    for r in rows:
        ttl = r.get("ttl")
        if not ttl or r.get("action") != "keep":
            continue
        if date.fromisoformat(ttl) <= today:
            due_rows.append(r)
    if not due_rows:
        print("无到期的 keep 决策。")
        return
    print("以下 keep 决策已到期，需重新审视：\n")
    for r in due_rows:
        print(f"  {r['skill']}  ttl={r['ttl']}  reason={r.get('reason','')}")
        print(f"    场景: {r.get('scenario_tag') or '-'}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_rec = sub.add_parser("record")
    p_rec.add_argument("--skill", required=True)
    p_rec.add_argument("--action", required=True, choices=["keep", "retire"])
    p_rec.add_argument("--reason", required=True)
    p_rec.add_argument("--override", action="store_true", default=False)
    p_rec.add_argument("--scenario-tag")
    p_rec.add_argument("--ttl", help="YYYY-MM-DD，仅 keep 生效")
    p_rec.add_argument("--by", default=DEFAULT_BY)

    p_list = sub.add_parser("list")
    p_list.add_argument("--skill")

    p_due = sub.add_parser("due")

    args = ap.parse_args()
    if args.cmd == "record":
        record(args)
    elif args.cmd == "list":
        list_(args)
    elif args.cmd == "due":
        due(args)


if __name__ == "__main__":
    main()
