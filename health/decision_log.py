#!/usr/bin/env python3
"""决策日志：人看数据做裁决，双向可 override，形成闭环。

**全部存本机，工具不往任何仓库写**：

    ~/.claude/health-decisions.jsonl

四条事实支撑这个选择：

1. **与工具自己的既定原则一致**——报告与快照都写在 gitignore 的 `report/` 下
   （「输出不过仓库」），决策日志没理由破例。
2. **它抑制的噪声是本机的**——触发来自本机转录，别的机器转录不同、报的东西也不同。
3. **写进共享仓库有真实的正确性问题**——两人各自对同一资产记录决策，追加式 JSONL 需要
   `merge=union`（当时为此配过，已随该方案移除），而 union 合并后 `latest_per_skill`
   取"最后一条"时，两台机器的追加顺序**没有意义**（谁先写取决于时钟），"最新"是任意的。
4. **变更理由本就该写在那个变更的 commit 里**——人执行 retire/promote 时会提交到
   对应仓库；再往工具状态文件存一份 = 第二份表示。

补充：动作会**自我了结**。真把某个 skill 从插件退役后，它就不在扫描范围内，任何机器
都不再报它。本文件里的那条决策只是「已决定、未执行」的中间态——所以它只需要本机可见。

内置与外部 marketplace 的资产**拒绝写入**：它们不出现在待裁决队列里，为其记录决策
没有意义（也避免"以为裁过了"的错觉）。

schema（每条一条 JSON）:
{
  "skill": "gen-commit",          # 哪个 skill/agent
  "action": "keep" | "retire"      # 用量侧：留着 / 下架
          | "promote" | "hold",    # 放置侧：上移共享 / 保持本地
  "override": false,               # 是否推翻评测结论
  "reason": "…",                   # 为什么（必填，且是下次复查时唯一的上下文）
  "ttl": "2026-10-01",             # 可选，仅保留类动作生效：到期重回队列
  "decided_at": "2026-09-03T...",  # 记录时间
  "by": "chenping26"               # 谁做的裁决
}

用法:
    python3 decision_log.py record --skill gen-commit --action keep --reason "..." [--ttl 2026-10-01]
    python3 decision_log.py list [--skill xxx]
    python3 decision_log.py due     # 列出 ttl 到期、需重新审视的 keep
"""
import argparse
import json
import os
from datetime import datetime, date, timezone

from asset_inventory import (BUILTIN, EXTERNAL_MARKETPLACES, build_source_map,
                             classify)
LOG_NAME = "health-decisions.jsonl"
DEFAULT_BY = os.environ.get("USER", "unknown")

# 决策日志的唯一落点（本机；工具不往任何仓库写）
USER_LOG = os.path.join(os.path.expanduser("~"), ".claude", LOG_NAME)
DEFAULT_SCAN_ROOT = os.path.join(os.path.expanduser("~"), "workspace")

# 两个维度共用一份日志（都是「对某个资产的人工判断 + 理由」），动作词表按问题类型分：
#   用量侧：keep（留着）/ retire（下架）
#   放置侧：promote（上移共享）/ hold（保持本地）
# 保留类动作可带 ttl，到期重回队列；终结类动作（retire / promote）不再催办。
RETAIN_ACTIONS = {"keep", "hold"}
ACTIONS = ("keep", "retire", "promote", "hold")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_log_for(source: str):
    """决策写到哪 —— 只有本机一处；不可裁决的资产直接拒绝。

    调用方只需知道「能不能记、记哪」；存放位置不再有分支，故这个函数只做准入判断。
    """
    if not source or source == BUILTIN:
        return None, "内置资产（磁盘上无对应文件），不在待裁决队列里"
    parts = source.split("+")
    if all(p.startswith("plugin:") and p.split(":", 1)[1] in EXTERNAL_MARKETPLACES
           for p in parts):
        return None, f"只存在于外部 marketplace（{'、'.join(parts)}），不是你的资产"
    return USER_LOG, "本机"


def _read(path: str) -> list:
    rows = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        pass
    return rows


def load_decisions() -> list:
    """读取全部裁决。只有本机一处——工具不往任何仓库写。"""
    return _read(USER_LOG)


def latest_per_skill(decisions):
    """{资产名: 最近一条裁决}。同一资产可有多次裁决，追加序即时间序，后者胜。"""
    out = {}
    for r in decisions:
        if r.get("skill"):
            out[r["skill"]] = r
    return out


def review_due(rec, today=None):
    """该裁决是否已到「需重新审视」的时候。

    只有「保留类」动作（keep / hold）+ 有 ttl + ttl 已到 → True（重回队列）。
    其余（retire / promote / 无 ttl / ttl 未到）→ False，即**不该再催办**。
    """
    ttl = rec.get("ttl")
    if rec.get("action") not in RETAIN_ACTIONS or not ttl:
        return False
    try:
        return date.fromisoformat(ttl) <= (today or date.today())
    except ValueError:
        return False


def record(args):
    root = getattr(args, "root", None) or DEFAULT_SCAN_ROOT
    sources = build_source_map(root)
    # 资产名可能属于 skill 也可能属于 agent，而使用者未必记得带 --kind。
    # 只按给定 kind 判会落到 builtin 而被误拒，故两种都试，取能定源的那个。
    kind = args.kind
    source = classify((kind, args.skill), sources)
    if source == BUILTIN:
        other = "agent" if kind == "skill" else "skill"
        alt = classify((other, args.skill), sources)
        if alt != BUILTIN:
            kind, source = other, alt
    path, desc = resolve_log_for(source)
    if path is None:
        print(f"✘ 拒绝写入：{args.skill} —— {desc}")
        print("  （只记你自己资产的判断，且只存本机）")
        return 1
    rec = {
        "skill": args.skill,
        "kind": kind,
        "action": args.action,
        "override": args.override,
        "reason": args.reason,
        "ttl": args.ttl,
        "decided_at": _now(),
        "by": args.by,
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"已记录裁决：{rec['skill']} -> {rec['action']} (override={rec['override']})")
    print(f"  落点：{desc}")
    print(f"  文件：{path}")
    return 0


def list_(args):
    rows = load_decisions()
    if args.skill:
        rows = [r for r in rows if r["skill"] == args.skill]
    if not rows:
        print("无决策记录。")
        return
    print(f"{'skill':<22} {'kind':<6} {'action':<8} {'override':<9} {'ttl':<12} "
          f"{'by':<10} reason")
    print("-" * 96)
    for r in rows:
        print(f"{r['skill']:<22} {r.get('kind') or '-':<6} {r['action']:<8} "
              f"{str(r.get('override')):<9} {r.get('ttl') or '-':<12} "
              f"{(r.get('by') or '-'):<10} {r.get('reason', '')}")


def due(args):
    """列出保留类动作中 ttl 已到期、需重新审视的裁决。"""
    today = date.today()
    # 只看每个资产的**最近一条**裁决：否则「先 keep（ttl 过期）后 retire」的资产
    # 会被旧记录一直拉回队列
    rows = latest_per_skill(load_decisions())
    due_rows = [r for r in rows.values() if review_due(r, today)]
    if not due_rows:
        print("无到期的保留决策。")
        return
    print("以下裁决已到期，需重新审视：\n")
    for r in due_rows:
        print(f"  {r['skill']}  ttl={r['ttl']}  action={r['action']}  "
              f"reason={r.get('reason', '')}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_common(p):
        p.add_argument("--root", default=DEFAULT_SCAN_ROOT,
                       help="项目扫描根目录，用于判定资产来源与作用域（默认 ~/workspace）")

    p_rec = sub.add_parser("record")
    p_rec.add_argument("--skill", required=True)
    p_rec.add_argument("--kind", default="skill", choices=["skill", "agent"],
                       help="资产类型（默认 skill）")
    p_rec.add_argument("--action", required=True, choices=list(ACTIONS),
                       help="keep/retire（用量侧：留/下架）｜promote/hold（放置侧：上移/保持本地）")
    p_rec.add_argument("--reason", required=True)
    p_rec.add_argument("--override", action="store_true", default=False)
    p_rec.add_argument("--ttl", help="YYYY-MM-DD，仅 keep/hold 生效")
    p_rec.add_argument("--by", default=DEFAULT_BY)
    add_common(p_rec)

    p_list = sub.add_parser("list")
    p_list.add_argument("--skill")
    add_common(p_list)

    p_due = sub.add_parser("due")
    add_common(p_due)

    args = ap.parse_args()
    if args.cmd == "record":
        return record(args)
    if args.cmd == "list":
        list_(args)
    elif args.cmd == "due":
        due(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main() or 0)
