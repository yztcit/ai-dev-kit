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
import hashlib
import json
import os
import re
import subprocess
from collections import defaultdict

HOME = os.path.expanduser("~")
MARKETPLACES = os.path.join(HOME, ".claude", "plugins", "marketplaces")
SKIP_DIRS = {"node_modules", ".git", "dist", "build", "out", "target", ".venv", "vendor"}


def find_project_claude_dirs(root):
    """找出 root 下所有项目级 .claude 目录（跳过依赖/产物目录）。"""
    found = []
    for dirpath, dirnames, _files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
                       or d == ".claude"]
        if os.path.basename(dirpath) == ".claude":
            found.append(dirpath)
            dirnames[:] = []          # 不往 .claude 里面继续找
    return found


def collect_assets(base, prefix):
    """从 <base>/{skills,agents} 收集 (kind, name) -> 内容哈希。"""
    out = {}
    for kind, pattern in (("skill", "skills"), ("agent", "agents")):
        d = os.path.join(base, pattern)
        if not os.path.isdir(d):
            continue
        if kind == "skill":
            for sub in os.listdir(d):
                f = os.path.join(d, sub, "SKILL.md")
                if os.path.isfile(f):
                    out[(kind, sub)] = file_hash(f)
        else:
            for fn in os.listdir(d):
                if fn.endswith(".md"):
                    out[(kind, fn[:-3])] = file_hash(os.path.join(d, fn))
    return out


def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:8]


def repo_identity(project_root):
    """用 git remote 判断「同一个项目的多份副本」，避免把副本误算成两个项目。"""
    try:
        url = subprocess.run(
            ["git", "-C", project_root, "config", "--get", "remote.origin.url"],
            capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        url = ""
    return url or os.path.realpath(project_root)


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
            shared |= set(collect_assets(os.path.join(plugins_dir, plugin), "").keys())
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
        for key, h in collect_assets(claude_dir, "").items():
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

    # 一行摘要：通知横幅宽度有限，塞表格原文只会变成噪声
    brief = ("无晋升候选" if not candidates else
             f"{len(candidates)} 个晋升候选：{'、'.join(c['name'] for c in candidates)}")

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
        return
    print(f"⚠️ 晋升候选（{len(candidates)} 个）：项目层跨多个项目重复、共享层缺位\n")
    print(f"{'能力':<28} {'类型':<6} {'项目数':>5} {'状态':<14} 位置")
    print("-" * 96)
    for c in candidates:
        print(f"{c['name']:<28} {c['kind']:<6} {c['projects']:>5} {c['state']:<14} "
              f"{', '.join(c['where'])}")
    print("\n注：只 flag，不动作。去语境化后由人裁决上移（设计文档 §4.4）。")


if __name__ == "__main__":
    main()
