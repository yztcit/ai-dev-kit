#!/usr/bin/env python3
"""决策日志：人看数据做裁决，双向可 override，形成闭环。

**按判断的作用域存放，不按资产所属层存放**：

    项目层资产（本机使用判断） → ~/.claude/health-decisions.jsonl   ← 不进任何项目
    团队层资产（对共享能力的立场）→ <团队仓库>/.claude/health-decisions.jsonl
    公共层资产（对共享能力的立场）→ 本仓库 .claude/health-decisions.jsonl

**为什么项目层判断不进项目**：业务项目不该承载工具状态——那是"哪个 skill 冷门"
这类本机账，混进业务仓库只会变成 `git status` 噪声，甚至进业务 git 历史。
本工具自己的既定模式就是「输出不过仓库」（报告与快照都写在 gitignore 的 report/），
决策日志不该破例。

**为什么共享层判断仍进对应仓库**：那是**对共享能力的立场**（"这个 skill 是按需调用，
别下架"），换个人、换台机器跑同一个工具时用得上，属于该层的能力定义的一部分。
顺带，公共仓库因此**天然不含业务语境**（项目层判断根本不会流进去）。

读取是**跨作用域聚合**的：`list` / `due` / 两个扫描器都读全部（用户级 + 各层仓库），
所以你看得到所有裁决。

团队层的仓库路径写在用户级配置 `~/.claude/health-layers.json`（机器特定，不进任何仓库）：

    {"marketplaces": {"<marketplace 名>": "<该层仓库的本地检出路径>"}}

未配置的 marketplace 会被拒绝写入并提示——宁可不写，也不写错地方。

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

from asset_inventory import (BUILTIN, EXTERNAL_MARKETPLACES, PUBLIC_MARKETPLACE,
                             REPO_ROOT, build_source_map, classify)
LOG_NAME = "health-decisions.jsonl"
DEFAULT_BY = os.environ.get("USER", "unknown")

# 项目层判断的本机落点（不进任何项目仓库）
USER_LOG = os.path.join(os.path.expanduser("~"), ".claude", LOG_NAME)

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


def all_log_paths(from_projects: list = None) -> list:
    """所有决策文件路径（跨作用域聚合读取用）。

    只有三处：用户级（项目层判断）+ 各共享层仓库。项目目录**不参与**——
    本工具不在业务项目里留任何文件。`from_projects` 仅供兼容旧布局的迁移使用。
    """
    paths = [USER_LOG, log_path(REPO_ROOT)]
    paths += list(team_logs().values())
    paths += list(from_projects or [])
    return paths


def resolve_log_for(source: str, root: str = None):
    """按资产所属层决定这条决策该写到哪。

    返回 (路径, 层描述) 或 (None, 拒绝原因)。拒绝时不写——宁可不记，
    也不把业务语境写进与之无关的层。
    """
    if not source or source == BUILTIN:
        return None, "内置资产（磁盘上无对应文件），不属于任何层"
    parts = source.split("+")
    # 项目层判断写用户级——**不进项目仓库**：那是本机使用判断，业务项目不该承载
    # 工具状态（会成为 git status 噪声，甚至进业务 git 历史）
    for p in parts:
        if p.startswith("project:"):
            return USER_LOG, "本机（项目层资产的使用判断）"
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


def load_decisions() -> list:
    """跨作用域聚合读取全部裁决（用户级 + 各共享层仓库）。"""
    rows = []
    for p in all_log_paths():
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
        print("  （判断按作用域存放：项目层→本机，共享层→该层仓库；无归属就不记）")
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
