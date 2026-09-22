#!/usr/bin/env python3
"""流水线 A：转录解析脚本（零埋点）。

从 ~/.claude/projects/<项目>/*.jsonl 的真实会话转录中，提取 Skill 与 Agent
（子代理）调用的 tool_use 事件，聚合出按资产的健康信号：
调用次数 / 最近使用 / 冷门度 / 重试率 / 失败次数。

用法:
    python3 scan_skill_usage.py [--days 30] [--retry-window-sec 600] [--json]
    python3 scan_skill_usage.py --snapshot report/skill-usage-history.jsonl

数据来源（v4 实测确认，v2 扩展）:
    ~/.claude/projects/<项目>/*.jsonl
    每行一条 JSON，调用位于 message.content[] 中:
        Skill : {type:"tool_use", id, name:"Skill", input:{skill:"<名>", args}}
        Agent : {type:"tool_use", id, name:"Agent"|"Task", input:{subagent_type:"<名>"}}
    结果位于 type=="user" 的行，content[].type=="tool_result"，以 tool_use_id 关联，
    is_error 标记该次调用本身失败。
    行级带 timestamp(ISO8601)、sessionId。
    <session>/subagents/*.jsonl 是子代理内部转录，不参与统计（调用记录在父转录里）。

覆盖范围（v2 修正 v1 的两个盲区）:
    1. v1 只解析 name=="Skill"，插件里的 Agent 资产（占一半）完全不可见。
    2. v1 的 --days 默认 90，而源转录只有 ~30 天寿命（Claude Code cleanupPeriodDays
       默认 30），窗口是假的，且把「证据过期」读成「无例外」→ 假阴性。
       v2 显式报出窗口，并用 --snapshot 落 append-only 快照，使时间序列不随源过期而丢失。
"""
import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from asset_inventory import build_source_map, classify, is_actionable
from decision_log import latest_per_skill, load_decisions, review_due

PROJECTS_DIR = os.path.expanduser("~/.claude/projects")
HOME = os.path.expanduser("~")


def short_source(src):
    """来源标注压短，便于进表格列。"""
    if src == "builtin":
        return "内置"
    parts = []
    for s in src.split("+"):
        if s.startswith("plugin:"):
            parts.append(f"插件:{s.split(':', 1)[1]}")
        elif s.startswith("project:"):
            parts.append(f"项目:{os.path.basename(s.split(':', 1)[1])}")
        else:
            parts.append(s)
    return "+".join(parts)


def row_tags(a, cold_days):
    tags = []
    if is_cold(a, cold_days):
        tags.append("冷门")
    if is_flaky(a):
        tags.append("高重试")
    if is_failing(a):
        tags.append("高失败")
    return ",".join(tags)


def row_line(name, a, cold_days, with_tags=True):
    return (f"{name:<22} {a['kind']:<6} {short_source(a['source']):<30} "
            f"{a['count']:>4} {a['sessions']:>4} {a['retries']:>4} "
            f"{a['failures']:>4} {a['last_days_ago']:>6}  "
            f"{row_tags(a, cold_days) if with_tags else ''}")


TABLE_HEAD = (f"{'资产':<22} {'类型':<6} {'来源':<30} {'调用':>4} {'会话':>4} "
              f"{'重试':>4} {'失败':>4} {'最近':>6}  标记")
TABLE_RULE = "-" * 100


def parse_ts(s: str) -> datetime:
    # 兼容 "2026-08-12T11:59:11.639Z" 与无小数秒
    s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def canonical(raw: str) -> str:
    """规范化资产名。

    转录里同一资产有裸名（`frontend-design`）与插件前缀名（`dev:code-reviewer`）
    两种记法（Skill 与 Agent 皆然）。取冒号后最后一段作为身份，把两种记法归并，
    避免冷门度被拆散误判。
    """
    return raw.rsplit(":", 1)[-1]


def iter_transcripts():
    """产出所有父转录文件路径（跳过 subagents/ 子代理内部转录）。"""
    if not os.path.isdir(PROJECTS_DIR):
        return
    for proj in os.listdir(PROJECTS_DIR):
        proj_dir = os.path.join(PROJECTS_DIR, proj)
        if not os.path.isdir(proj_dir):
            continue
        for root, _dirs, files in os.walk(proj_dir):
            if os.path.basename(root) == "subagents":
                continue
            for fn in files:
                if fn.endswith(".jsonl"):
                    yield os.path.join(root, fn)


def extract_calls(path: str):
    """从单个转录提取本轮信息。

    返回 (calls, tool_results):
        calls: [(ts, sid, id, raw_name, kind, msg_key)]，kind ∈ {"skill", "agent"}
        tool_results: {tool_use_id: is_error}
    tool_use 与 tool_result 分行且以 id 关联，故需一次性扫完再回填。
    msg_key 标识「同一条 assistant 消息」：同消息内的多次调用是并行 fan-out
    （如一次派 3 个 Explore），不是重试，据此把它排除在重试统计外。
    """
    calls = []
    results = {}
    try:
        with open(path, encoding="utf-8") as f:
            for lineno, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                otype = obj.get("type")
                ts = obj.get("timestamp")
                sid = obj.get("sessionId", "")
                for c in obj.get("message", {}).get("content", []) or []:
                    if not isinstance(c, dict):
                        continue
                    ctype = c.get("type")
                    if ctype == "tool_use" and ts:
                        name = c.get("name")
                        inp = c.get("input") or {}
                        msg_key = obj.get("uuid") or f"{path}:{lineno}"
                        if name == "Skill" and inp.get("skill"):
                            calls.append((ts, sid, c.get("id"), inp["skill"],
                                          "skill", msg_key))
                        elif name in ("Agent", "Task"):
                            # subagent_type 可缺省（内置通用子代理）
                            calls.append((ts, sid, c.get("id"),
                                          inp.get("subagent_type") or "(general)",
                                          "agent", msg_key))
                    elif ctype == "tool_result" and c.get("tool_use_id") is not None:
                        results[c["tool_use_id"]] = bool(c.get("is_error"))
    except OSError:
        return [], {}
    return calls, results


def collect(days: int, retry_window_sec: int):
    """遍历全部转录，聚合成 {asset: stats}。"""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    agg = defaultdict(lambda: {"kind": None, "count": 0, "last_ts": None,
                               "sessions": set(), "retries": 0, "failures": 0})
    # 重试需按会话判定：跨会话的两次调用不是重试
    per_session = defaultdict(list)

    for path in iter_transcripts():
        calls, results = extract_calls(path)
        for ts_raw, sid, call_id, raw_name, kind, msg_key in calls:
            try:
                ts = parse_ts(ts_raw)
            except (ValueError, AttributeError):
                continue
            if ts < cutoff:
                continue
            name = canonical(raw_name)
            a = agg[name]
            a["kind"] = kind
            a["count"] += 1
            a["sessions"].add(sid)
            if results.get(call_id):
                a["failures"] += 1
            if a["last_ts"] is None or ts > a["last_ts"]:
                a["last_ts"] = ts
            per_session[(sid, name)].append((ts, msg_key))

    for (_sid, name), events in per_session.items():
        # 同一消息内的并行 fan-out 合并为一次调用，不计作重试
        first_per_msg = {}
        for ts, msg_key in events:
            if msg_key not in first_per_msg or ts < first_per_msg[msg_key]:
                first_per_msg[msg_key] = ts
        ts_list = sorted(first_per_msg.values())
        agg[name]["retries"] += sum(
            1 for i in range(1, len(ts_list))
            if (ts_list[i] - ts_list[i - 1]).total_seconds() <= retry_window_sec
        )

    for a in agg.values():
        a["sessions"] = len(a["sessions"])
        a["last_days_ago"] = (now - a["last_ts"]).days if a["last_ts"] else None
    return agg


def is_cold(a, cold_days):
    return a["last_days_ago"] is not None and a["last_days_ago"] >= cold_days


def is_flaky(a):
    return a["retries"] >= 2 and a["count"] < 5


def is_failing(a):
    return a["failures"] >= 2 and a["count"] < 5


def load_last_snapshot(path):
    """读快照文件最后一行（上一轮聚合），无则返回 None。"""
    if not path or not os.path.exists(path):
        return None
    last = None
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    last = line
    except OSError:
        return None
    if not last:
        return None
    try:
        return json.loads(last)
    except json.JSONDecodeError:
        return None


def save_snapshot(path, days, cold_days, agg):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "days": days,
        "cold_days": cold_days,
        "assets": {n: {"kind": a["kind"], "count": a["count"],
                       "sessions": a["sessions"], "retries": a["retries"],
                       "failures": a["failures"],
                       "last_days_ago": a["last_days_ago"]}
                   for n, a in agg.items()},
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30,
                    help="统计窗口（天）。注意源转录默认只保留 30 天，取更大值不会"
                         "拿到更早的数据——那部分已被清理，会表现为「无数据」而非「无例外」")
    ap.add_argument("--retry-window-sec", type=int, default=600,
                    help="同一会话内同资产在此窗口内再次调用记为一次重试")
    ap.add_argument("--json", action="store_true", help="输出 JSON 而非表格")
    ap.add_argument("--cold-days", type=int, default=14,
                    help="最近 N 天未用视为冷门，进例外队列。必须 < 保留期（默认 30 天）："
                         "等于或超过保留期时，资产在能被判冷门之前证据就已过期，"
                         "表现为「无数据」而非「冷门」，等于永远判不出来")
    ap.add_argument("--exceptions-only", action="store_true",
                    help="只输出例外队列（冷门 + 高重试 + 高失败），不输出全量表")
    ap.add_argument("--brief", action="store_true",
                    help="只输出一行摘要（人看）")
    ap.add_argument("--brief-file", metavar="FILE",
                    help="把一行摘要写到 FILE，供通知脚本用。与 --snapshot 同一次运行，"
                         "避免为了拿摘要而重跑扫描（重跑会让快照重复落盘）")
    ap.add_argument("--root", default=os.path.join(HOME, "workspace"),
                    help="项目扫描根目录，用于判定资产来源（默认 ~/workspace）")
    ap.add_argument("--snapshot", metavar="FILE",
                    help="把本轮聚合追加到 append-only 快照（使时间序列不随源过期丢失），"
                         "并与其最后一行对比报出「退出窗口」的资产")
    args = ap.parse_args()

    # 不变量：冷门阈值必须严格小于窗口/保留期。否则资产在「够冷」之前证据就已被清理，
    # 冷门永远不可判——这正是 v1 的静默失效（日志读起来是「无例外」）。
    if args.cold_days >= args.days:
        print(f"⚠️ 配置失效：--cold-days({args.cold_days}) ≥ --days({args.days})，"
              f"资产在够冷之前记录已过期，冷门永远判不出来。"
              f"应取小于保留期（默认 30 天）的值，如 14。\n")

    agg = collect(args.days, args.retry_window_sec)

    # 来源清点：例外队列只该收「你能裁决的」资产。内置（run / Explore / Plan）与
    # 别人的 marketplace（官方插件）不是你的库，把它们排进「需人裁决」是让人去做
    # 一件他做不到的事——队列里混进这种项，整份报告的可信度就没了。
    sources = build_source_map(args.root)
    for name, a in agg.items():
        a["source"] = classify((a["kind"], name), sources)

    rows = sorted(agg.items(), key=lambda kv: kv[1]["last_days_ago"] or 0, reverse=True)
    flagged = [(s, a) for s, a in rows
               if is_cold(a, args.cold_days) or is_flaky(a) or is_failing(a)]
    actionable = [(s, a) for s, a in flagged if is_actionable(a["source"])]
    inert = [(s, a) for s, a in flagged if not is_actionable(a["source"])]

    # 已裁决且未到复查日的，退出队列——否则「裁决完还在催」= 闭环没闭上，
    # 通知会每周重复同一件事，最后被整体无视。
    decided = latest_per_skill(load_decisions())
    exceptions, settled = [], []
    for name, a in actionable:
        rec = decided.get(name)
        if rec and not review_due(rec):
            settled.append((name, a, rec))
        else:
            exceptions.append((name, a))

    # 已裁决的资产名，**取自全部裁决**而非仅本轮标记项：一个「keep、按需调用」的资产
    # 迟早会滑出时间窗口，那时它已不在 agg 里，若只从标记项取就漏掉它。
    settled_names = {n for n, r in decided.items() if not review_due(r)}

    prev = load_last_snapshot(args.snapshot) if args.snapshot else None
    vanished, vanished_muted = [], []
    # 仅在同窗口下对比：窗口不同则「退出」只是口径差异，不是信号
    if prev and prev.get("days") == args.days:
        prev_assets = prev.get("assets") or {}
        for name in sorted(set(prev_assets) - set(agg)):
            # 已裁决的资产滑出窗口不是新闻——尤其「keep、按需调用」的，滑出是**预期**
            # （实测：某项目 skill 裁决时已 28 天未用，次周必滑出 → 否则通知会为一件已决定的事
            # 反复响）。要定期重新审视请用 --ttl，那是它的职责。
            (vanished_muted if name in settled_names else vanished).append(name)

    if args.snapshot:
        save_snapshot(args.snapshot, args.days, args.cold_days, agg)

    # 一行摘要：通知横幅宽度有限，塞表格原文只会变成噪声
    if not agg:
        brief = "无数据（窗口内无调用记录）"
    elif exceptions:
        brief = f"{len(exceptions)} 个待裁决：{'、'.join(n for n, _ in exceptions)}"
        if vanished:
            brief += f"；{len(vanished)} 个退出窗口"
    elif vanished:
        brief = f"无待裁决；{len(vanished)} 个退出窗口：{'、'.join(vanished)}"
    else:
        brief = f"无例外（{len(agg)} 个资产在用）"

    if args.brief_file:
        with open(args.brief_file, "w", encoding="utf-8") as f:
            f.write(brief + "\n")

    if args.brief:
        print(brief)
        return

    if args.json:
        out = {n: {"kind": a["kind"], "count": a["count"], "sessions": a["sessions"],
                   "retries": a["retries"], "failures": a["failures"],
                   "last_days_ago": a["last_days_ago"]}
               for n, a in rows}
        print(json.dumps({"window_days": args.days, "assets": out,
                          "vanished_from_window": vanished},
                         ensure_ascii=False, indent=2))
        return

    if args.exceptions_only:
        if not agg:
            # 「无数据」与「无例外」必须分开报——否则源过期会被读成健康
            print(f"无数据（近 {args.days} 天内无任何 Skill/Agent 调用记录；"
                  f"源转录仅保留约 30 天，更早的记录已清理）")
            return
        if not exceptions:
            print(f"无可裁决例外（窗口 {args.days} 天内有 {len(agg)} 个资产在用；"
                  f"扫描根 {args.root}）。")
            if settled:
                print(f"（{len(settled)} 个已被标记但**已裁决**，不再催办）")
        else:
            print(f"例外队列（冷门≥{args.cold_days}天 或 高重试 或 高失败；"
                  f"窗口 {args.days} 天）—— 只列**你能裁决的**资产：\n")
            print(TABLE_HEAD)
            print(TABLE_RULE)
            for name, a in exceptions:
                print(row_line(name, a, args.cold_days))
        if settled:
            # 让「裁决生效了」可见——否则用户不知道自己那笔裁决有没有起作用
            print(f"\n已裁决，退出队列（不再催办）：")
            for name, _a, rec in settled:
                extra = f"，复查日 {rec['ttl']}" if rec.get("ttl") else ""
                print(f"  - {name}（{rec.get('action')}{extra}：{rec.get('reason', '')}）")
        if inert:
            # 内置与别人的 marketplace 不是你的库，不能悄悄吞掉——列出来但标明无需裁决。
            # 必须连扫描根一起报：项目若在根之外，会被归为「内置」而静默排除出队列，
            # 那是假阴性（同「证据过期读成健康」一类）。
            print(f"\n另有 {len(inert)} 项非本库资产被标记，**无需裁决**"
                  f"（内置，或位于扫描根之外：{args.root}）：")
            for name, a in inert:
                print(f"  - {name}（{short_source(a['source'])}，{row_tags(a, args.cold_days)}）")
        if vanished:
            print(f"\n⚠️ 退出窗口：{', '.join(vanished)}"
                  f"（上轮在窗口内、本轮已滑出——可能是真冷门，也可能是记录过期，"
                  f"两者从此处起无法区分，判冷门前先查源是否还在）")
        if vanished_muted:
            print(f"\n（{len(vanished_muted)} 个已裁决资产滑出窗口，已静音："
                  f"{'、'.join(vanished_muted)}——滑出对它们不是新闻）")
        if exceptions:
            print("\n裁决（决定后执行；keep 可加 --ttl YYYY-MM-DD 到期重回队列）：")
            for name, _a in exceptions:
                print(f"  python3 ~/.claude/scripts/decision_log.py record "
                      f"--skill {name} --action keep|retire --reason \"…\"")
            print("  查看：python3 ~/.claude/scripts/decision_log.py list"
                  " ｜ 到期复查：… due")
        return

    if not rows:
        print(f"近 {args.days} 天内无 Skill/Agent 调用记录"
              f"（源转录默认只保留 30 天，更早的记录已被清理）。")
        return

    print(f"近 {args.days} 天内的调用统计（重试窗口 {args.retry_window_sec}s）\n")
    print(TABLE_HEAD)
    print(TABLE_RULE)
    for name, a in rows:
        print(row_line(name, a, args.cold_days, with_tags=False))

    if exceptions:
        print(f"\n⚠️ 例外队列（需人裁决）：{len(exceptions)} 个")
        for name, a in exceptions:
            print(f"  - {name}（{short_source(a['source'])}，{row_tags(a, args.cold_days)}）")
    if settled:
        names = "、".join(f"{n}（{r.get('action')}）" for n, _a, r in settled)
        print(f"\n✅ 已裁决、退出队列：{len(settled)} 个 —— {names}")
    if inert:
        print(f"\nℹ️ 非本库资产（内置 / 别人的 marketplace，无需裁决）：{len(inert)} 个 —— "
              f"{'、'.join(n for n, _ in inert)}")
    if vanished:
        print(f"\n⚠️ 退出窗口：{', '.join(vanished)}")
    if vanished_muted:
        print(f"\n（{len(vanished_muted)} 个已裁决资产滑出窗口，已静音："
              f"{'、'.join(vanished_muted)}）")


if __name__ == "__main__":
    main()
