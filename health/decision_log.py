#!/usr/bin/env python3
"""决策日志：人看数据做裁决，双向可 override，形成闭环。

**分层存储（关键）**：决策跟随**资产所属层**存放，而不是集中在一处。

    项目层资产 → <项目>/.claude/health-decisions.jsonl
    团队层资产 → <团队仓库>/.claude/health-decisions.jsonl
    公共层资产 → 本仓库 .claude/health-decisions.jsonl

为什么必须分层：三层体系的公共层明令「不含任何业务/团队语境」，而裁决理由天然
带业务语境（"某某产品线的 agent，迭代时才用"）。把项目层资产的裁决记进公共仓库，
就是往公共层灌业务语境——违反它自己的准入判据。分层之后，项目层决策若落在
gitignore 掉的 .claude/ 里，天然就不共享，这**正是**该有的结果。

读取是**跨层聚合**的：`list` / `due` / 两个扫描器都会读全部层，所以你看得到所有裁决。

团队层的仓库路径写在用户级配置 `~/.claude/health-layers.json`（机器特定，不进任何仓库）：

    {"marketplaces": {"<marketplace 名>": "<该层仓库的本地检出路径>"}}

未配置的 marketplace 会被拒绝写入并提示——宁可不写，也不把业务内容塞进公共层。

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

from asset_inventory import (BUILTIN, EXTERNAL_MARKETPLACES, PUBLIC_MARKETPLACE, REPO_ROOT,
                             build_source_map, classify, find_project_claude_dirs)
LOG_NAME = "health-decisions.jsonl"
DEFAULT_BY = os.environ.get("USER", "unknown")

# 团队层的本地仓库路径（机器特定 → 放用户级，不进任何仓库）
LAYER_CONFIG = os.path.join(os.path.expanduser("~"), ".claude", "health-layers.json")
DEFAULT_SCAN_ROOT = os.path.join(os.path.expanduser("~"), "workspace")

# 两个维度共用一份日志（都是「对某个资产的人工判断 + 理由」），动作词表按问题类型分：
#   用量侧：keep（留着）/ retire（下架）
#   放置侧：promote（上移共享）/ hold（保持本地）
# 保留类动作可带 ttl，到期重回队列；终结类动作（retire / promote）不再催办。
RETAIN_ACTIONS = {"keep", "hold"}
ACTIONS = ("keep", "retire", "promote", "hold")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_path(layer_root: str) -> str:
    """任一层的决策文件路径。全层统一 <层根>/.claude/health-decisions.jsonl。"""
    return os.path.join(layer_root, ".claude", LOG_NAME)


def team_logs() -> dict:
    """{marketplace 名: 该层决策文件路径}，来自用户级层配置。"""
    try:
        with open(LAYER_CONFIG, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    out = {}
    for mkt, repo in (cfg.get("marketplaces") or {}).items():
        if isinstance(repo, str) and repo:
            out[mkt] = log_path(os.path.expanduser(repo))
    return out


def all_log_paths(root: str = None) -> list:
    """所有层的决策文件路径（跨层聚合读取用）。"""
    paths = [log_path(REPO_ROOT)]
    paths += list(team_logs().values())
    for claude_dir in find_project_claude_dirs(root or DEFAULT_SCAN_ROOT):
        paths.append(os.path.join(claude_dir, LOG_NAME))
    return paths


def resolve_log_for(source: str, root: str = None):
    """按资产所属层决定这条决策该写到哪。

    返回 (路径, 层描述) 或 (None, 拒绝原因)。拒绝时不写——宁可不记，
    也不把业务语境写进与之无关的层。
    """
    if not source or source == BUILTIN:
        return None, "内置资产（磁盘上无对应文件），不属于任何层"
    parts = source.split("+")
    # 项目层最具体，优先
    for p in parts:
        if p.startswith("project:"):
            proj = p.split(":", 1)[1]
            return log_path(proj), f"项目层（{proj}）"
    # 同名资产可能同时在多处存在（实测：code-reviewer 官方与团队都有），
    # 故先找**能落地的层**，别取到第一个（外部 marketplace）就拒绝。
    teams = team_logs()
    unconfigured = []
    for p in parts:
        if p.startswith("plugin:"):
            mkt = p.split(":", 1)[1]
            if mkt == PUBLIC_MARKETPLACE:
                return log_path(REPO_ROOT), f"公共层（{mkt}）"
            if mkt in teams:
                return teams[mkt], f"团队层（{mkt}）"
            unconfigured.append(mkt)
    if unconfigured:
        own = [m for m in unconfigured if m not in EXTERNAL_MARKETPLACES]
        if own:
            m = own[0]
            return None, (f"marketplace '{m}' 未配置本地仓库路径。"
                          f"请在 {LAYER_CONFIG} 里登记该层仓库后重试"
                          f"（形如 {{\"marketplaces\": {{\"{m}\": \"/path/to/repo\"}}}}）")
        return None, (f"只存在于外部 marketplace（{'、'.join(unconfigured)}），"
                      f"不属于你的任何层")
    return None, f"无法归类到任何层：{source}"


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


def load_decisions(root: str = None) -> list:
    """跨层聚合读取全部裁决。"""
    rows = []
    for p in all_log_paths(root):
        rows += _read(p)
    return rows


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


def settled(rec, today=None):
    """这条裁决是否已经「了结」——了结 = 不该再出现在待裁决队列里。"""
    return not review_due(rec, today)


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
    path, desc = resolve_log_for(source, root)
    if path is None:
        print(f"✘ 拒绝写入：{args.skill} —— {desc}")
        print("  （决策跟随资产所属层存放；无归属就不记，避免业务语境污染无关层）")
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
    print(f"  写入层：{desc}")
    print(f"  文件：{path}")
    return 0


def list_(args):
    rows = load_decisions(getattr(args, "root", None))
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
    rows = latest_per_skill(load_decisions(getattr(args, "root", None)))
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
                       help="项目扫描根目录，用于判定资产所属层（默认 ~/workspace）")

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
