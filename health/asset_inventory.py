#!/usr/bin/env python3
"""资产来源清点：回答「这个 skill / agent 是谁的」。

来源一律取自**文件系统**，不猜：

    plugin:<marketplace>   —— 装在某个 marketplace 下的插件载荷
    project:<项目根路径>    —— 某个项目 .claude/{skills,agents} 下的项目层资产
    builtin                —— 以上都找不到 → Claude Code 内置（磁盘上没有对应文件）

**为什么需要它**：巡检的「例外队列」只该包含**你能裁决的**资产——自己的插件 + 自己的
项目层。内置（`run` / `Explore` / `Plan`）与官方插件（`frontend-design`）不是你的库，
把它们排进「需人裁决」是让人去决定一件他做不到的事；一旦队列里混进这种项，整份报告
的可信度就没了（实测：4 项例外里 2 项属此类）。

用法：
    from asset_inventory import build_source_map, classify
    sources = build_source_map(root)          # {(kind, name): {来源, ...}}
    classify(("skill", "run"), sources)       # -> "builtin"
"""
import hashlib
import os
import subprocess

HOME = os.path.expanduser("~")
MARKETPLACES = os.path.join(HOME, ".claude", "plugins", "marketplaces")
SKIP_DIRS = {"node_modules", ".git", "dist", "build", "out", "target", ".venv", "vendor"}

# 本仓库（公共层）自身：它的 plugins/ 不经 marketplace 注册，须单独扫，
# 否则公共层资产会被误判成 builtin（内置）而排除出可裁决范围。
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def _public_marketplace_name():
    import json
    try:
        with open(os.path.join(REPO_ROOT, ".claude-plugin", "marketplace.json"),
                  encoding="utf-8") as f:
            return json.load(f).get("name") or "public-layer"
    except (OSError, ValueError):
        return "public-layer"


PUBLIC_MARKETPLACE = _public_marketplace_name()

BUILTIN = "builtin"

# 别人的 marketplace：装在你机器上、但不由你维护，不该进「需你裁决」的队列。
# 默认只列官方那一个；自家/团队的 marketplace 一律视为可裁决。
EXTERNAL_MARKETPLACES = {"claude-plugins-official"}


def repo_identity(project_root):
    """用 git remote 判断「同一个项目的多份副本」，避免把副本算成两个项目。"""
    try:
        url = subprocess.run(
            ["git", "-C", project_root, "config", "--get", "remote.origin.url"],
            capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        url = ""
    return url or os.path.realpath(project_root)


def find_project_claude_dirs(root):
    """找出 root 下所有项目级 .claude 目录（跳过依赖与产物目录）。"""
    found = []
    for dirpath, dirnames, _files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS or d == ".claude"]
        if os.path.basename(dirpath) == ".claude":
            found.append(dirpath)
            dirnames[:] = []          # 不往 .claude 里面继续找
    return found


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()[:8]


def collect_assets(base):
    """从 <base>/{skills,agents} 收集 {(kind, name): 内容哈希}。

    带哈希是因为放置侧还要比较「同一能力在不同项目里是否已分叉」；
    只要键的调用方直接忽略值即可。
    """
    out = {}
    for kind, sub in (("skill", "skills"), ("agent", "agents")):
        d = os.path.join(base, sub)
        if not os.path.isdir(d):
            continue
        for entry in os.listdir(d):
            if kind == "skill":
                f = os.path.join(d, entry, "SKILL.md")
                if os.path.isfile(f):
                    out[(kind, entry)] = file_hash(f)
            elif entry.endswith(".md"):
                out[(kind, entry[:-3])] = file_hash(os.path.join(d, entry))
    return out


def build_source_map(root):
    """{(kind, name): {来源, ...}}。

    同一名字可能在多处存在（如内置也有 code-review、你的插件也有 code-review），
    故值是**集合**——别把多来源压成一个，否则分类会骗人。
    """
    sources = {}

    def add(key, src):
        sources.setdefault(key, set()).add(src)

    # 公共层：本仓库自己的 plugins/（不经 marketplace 注册）
    own_plugins = os.path.join(REPO_ROOT, "plugins")
    if os.path.isdir(own_plugins):
        for plugin in os.listdir(own_plugins):
            for key in collect_assets(os.path.join(own_plugins, plugin)):
                add(key, f"plugin:{PUBLIC_MARKETPLACE}")

    # 插件层：已装 marketplace 的载荷
    if os.path.isdir(MARKETPLACES):
        for mkt in os.listdir(MARKETPLACES):
            plugins_dir = os.path.join(MARKETPLACES, mkt, "plugins")
            if not os.path.isdir(plugins_dir):
                continue
            for plugin in os.listdir(plugins_dir):
                for key in collect_assets(os.path.join(plugins_dir, plugin)):
                    add(key, f"plugin:{mkt}")

    # 项目层：同一仓库的多份检出（不同目录/分支）只算一个项目，
    # 否则 `projects/x` 与 `projects/lui/x` 会显示成两个项目、看起来像 bug。
    representative = {}
    for claude_dir in find_project_claude_dirs(root):
        project_root = os.path.dirname(claude_dir)
        path = representative.setdefault(repo_identity(project_root), project_root)
        for key in collect_assets(claude_dir):
            add(key, f"project:{path}")

    return sources


def classify(key, sources):
    """给定 (kind, name) 返回来源标注。

    磁盘上找不到 → builtin。多来源时合并显示（如 `plugin:<你的>+plugin:<外部>`）——
    这正说明该名字有歧义，不该假装能分辨（实测：官方市场的 feature-dev 与
    团队的 dev 插件都有 code-reviewer）。
    """
    found = sources.get(key)
    return "+".join(sorted(found)) if found else BUILTIN


def is_actionable(source, external=EXTERNAL_MARKETPLACES):
    """能不能由使用者裁决（下架 / 上移）。

    - `project:*`                  → 能（项目层是自己的）
    - `plugin:<非外部 marketplace>` → 能（自家/团队的插件库）
    - `plugin:<外部 marketplace>`   → 不能（别人的库，不该进「需你裁决」）
    - `builtin`                    → 不能（磁盘上都没有，无从下架）
    """
    for part in source.split("+"):
        if part.startswith("project:"):
            return True
        if part.startswith("plugin:"):
            if part.split(":", 1)[1] not in external:
                return True
    return False
