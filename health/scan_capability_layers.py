#!/usr/bin/env python3
"""分层错置检测：找出「放错层」的能力（晋升候选）。

背景：三层体系（项目业务 → 团队共用 → 公共通用）定义了晋升规则，但从来没有
信号能指出「该晋升什么」——`scan_skill_usage.py` 的三类例外（冷门/高重试/高失败）
全部指向退役，晋升方向信号为零。本脚本补上另一半：只看**放置**，不看用量。

判据（确定性，无需 LLM）：
    某能力在 ≥2 个**不同项目**的项目层各自存在，而共享层（已装 marketplace 的载荷）
    没有它 → 它就是「已被多个项目独立重复、本该共享」的晋升候选。
    内容的两种形态分别标注：
      - 逐字相同：最直接的通用证据（同一份文本在多处适用）
      - 已分叉：说明各项目已开始各自维护，漂移成本正在产生

注意：本脚本只 **flag**，不做任何动作。去语境化是语义动作，由人裁决后手工上移
（对齐设计文档 §4.4「检测与决策分离」）。

用法:
    python3 scan_capability_layers.py [--root ~/workspace] [--json]

数据源：
    项目层 = <root>/**/.claude/{skills,agents}
    共享层 = ~/.claude/plugins/marketplaces/*/plugins/*/{skills,agents}
"""
import argparse
import json
import os
import subprocess
from collections import defaultdict

from asset_inventory import (HOME, MARKETPLACES, collect_assets,
                             find_project_claude_dirs, repo_identity)
from decision_log import latest_per_skill, load_decisions, review_due


def collect_shared():
    """共享层 = 已装 marketplace 的载荷。"""
    shared = set()
    if not os.path.isdir(MARKETPLACES):
        return shared
    for mkt in os.listdir(MARKETPLACES):
        plugins_dir = os.path.join(MARKETPLACES, mkt, "plugins")
        if not os.path.isdir(plugins_dir):
            continue
        for plugin in os.listdir(plugins_dir):
            shared |= set(collect_assets(os.path.join(plugins_dir, plugin)).keys())
    return shared


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join(HOME, "workspace"),
                    help="项目扫描根目录（默认 ~/workspace）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--brief", action="store_true",
                    help="只输出一行摘要（人看）")
    ap.add_argument("--brief-file", metavar="FILE",
                    help="把一行摘要写到 FILE，供通知脚本用")
    args = ap.parse_args()

    # (kind, name) -> {repo_identity: {内容哈希: 项目根路径}}
    seen = defaultdict(lambda: defaultdict(dict))
    for claude_dir in find_project_claude_dirs(args.root):
        project_root = os.path.dirname(claude_dir)
        ident = repo_identity(project_root)
        for key, h in collect_assets(claude_dir).items():
            seen[key][ident][h] = project_root

    shared = collect_shared()

    candidates = []
    for (kind, name), repos in seen.items():
        if (kind, name) in shared:
            continue                                   # 已共享，不是候选
        if len(repos) < 2:
            continue                                   # 只有一个项目，留在项目层合理
        variants = {h for repo in repos.values() for h in repo}
        candidates.append({
            "kind": kind,
            "name": name,
            "projects": len(repos),
            "variants": len(variants),
            "state": "逐字相同" if len(variants) == 1 else f"已分叉（{len(variants)} 版）",
            "where": sorted({next(iter(repo.values())) for repo in repos.values()}),
        })
    candidates.sort(key=lambda c: (-c["projects"], c["name"]))

    # 已裁决的候选退出队列（与用量侧同构）——否则「决定完了还在催」，通知每周重复。
    # 注：promote（决定上移）是**有执行动作**的裁决，实际搬完之前候选不会自动消失，
    # 故它虽不再进通知，仍单独列出并标注「待执行」，避免搬运动作被遗忘。
    decided = latest_per_skill(load_decisions(args.root))
    open_c, settled_c = [], []
    for c in candidates:
        rec = decided.get(c["name"])
        if rec and not review_due(rec):
            settled_c.append((c, rec))
        else:
            open_c.append(c)

    # 一行摘要：通知横幅宽度有限，塞表格原文只会变成噪声
    brief = ("无晋升候选" if not open_c else
             f"{len(open_c)} 个晋升候选：{'、'.join(c['name'] for c in open_c)}")

    if args.brief_file:
        with open(args.brief_file, "w", encoding="utf-8") as f:
            f.write(brief + "\n")

    if args.brief:
        print(brief)
        return

    if args.json:
        print(json.dumps({"root": args.root, "candidates": candidates,
                          "shared_assets": len(shared)}, ensure_ascii=False, indent=2))
        return

    print(f"扫描根：{args.root}")
    print(f"共享层能力：{len(shared)} 个（已装 marketplace 载荷）\n")
    if not candidates:
        print("无晋升候选：项目层没有跨项目重复的能力。")
        if settled_c:
            print(f"（{len(settled_c)} 个曾报候选但**已裁决**）")
        return
    if open_c:
        print(f"⚠️ 晋升候选（{len(open_c)} 个）：项目层跨多个项目重复、共享层缺位\n")
        print(f"{'能力':<28} {'类型':<6} {'项目数':>5} {'状态':<14} 位置")
        print("-" * 96)
        for c in open_c:
            print(f"{c['name']:<28} {c['kind']:<6} {c['projects']:>5} {c['state']:<14} "
                  f"{', '.join(c['where'])}")
        print("\n裁决（决定后执行）：")
        for c in open_c:
            print(f"  python3 ~/.claude/scripts/decision_log.py record "
                  f"--skill {c['name']} --action promote|hold --reason \"…\"")
        print("  promote=上移共享层｜hold=保持本地（可加 --ttl YYYY-MM-DD 到期重回队列）")
    else:
        print("无未裁决的晋升候选。")
    if settled_c:
        print(f"\n已裁决，退出队列（不再催办）：")
        for c, rec in settled_c:
            todo = "　⚠️ 待执行：上移到共享层" if rec.get("action") == "promote" else ""
            print(f"  - {c['name']}（{rec.get('action')}：{rec.get('reason', '')}）{todo}")
    print("\n注：只 flag，不动作。去语境化是语义动作，由人裁决后手工上移（设计文档 §4.4）。")


if __name__ == "__main__":
    main()
