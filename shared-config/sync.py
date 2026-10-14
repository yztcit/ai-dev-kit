#!/usr/bin/env python3
"""把当前检出的 .claude 配置对齐到「主干检出」。会话开始时由 SessionStart hook 自动跑。

解决的是这件事：项目 .claude（agents / rules / skills / plans / settings.json）被 gitignore，
所以它跟着**检出目录**走。同一个仓库为了并行打开多个分支而建多个检出时，新检出根本没有 .claude，
或者各存一份互相漂移（实测：同一份 agent 文档一个 32KB 一个 16KB；某个 agent 只存在于其中一个检出）。

做法：不做软链、不额外开目录。各检出各留一份**真实**的 .claude，本脚本负责让**当前检出**跟上主干。

## 模型：主干权威，分支各自演进

这不是「让所有检出一模一样」，而是「分支从主干取，改动留在分支，完工再合回主干」——
和代码分支的语义一致。所以：

  主干检出（develop/main/master）  → 权威，本脚本只读它，从不改它
  其它检出                        → 只要这个文件**自己没动过**，就跟随主干（新增/更新/删除都跟）
                                    自己动过的 → 一律不动，那是本分支的工作成果，等合并

「自己动过没有」靠每个检出的 `.claude/.sync-state.json`（上次同步后各文件的大小/mtime/哈希）判断。

于是三种日常情形自动覆盖：
  新建检出目录、开会话      → 本地从没有过 .claude → 全部跟随主干 = 从主干 fork 一份
  分支没碰过文档、主干更新了 → 自动跟上（等价于 git 的快进）
  分支改了文档              → 不动；主干后来也改了同一个文件 → 仍不动，等你自己合并

## 已知边界

- **分支的文档改动不会自动回到主干**——那正是「完工后合并」这一步，需要人判断，交给 skill 做。
- 主干上删掉的文件，只有本地「没动过」时才会跟着删；本地改过的不会被删。
- 主干认定：$CLAUDE_SYNC_TRUNK 指定的分支名，否则依次找 develop / main / master；
  都没有就取第一个检出。
- 发现同仓库检出：扫 $CLAUDE_SYNC_ROOT（默认 ~/workspace）下带 .git 的目录，按**归一化
  git remote** 归组——不按目录名，因为「同名不同仓」「同仓不同路径」都会出现。

用法:
  sync.py [目录]      对齐（默认 $CLAUDE_PROJECT_DIR 或当前目录），有动作才输出
  sync.py --quiet     完全静默（hook 之外的脚本场景用）
  sync.py --status    只报告：主干是谁、本分支哪些文件与主干不同、是否已合并
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "health"))
from asset_inventory import normalize_remote  # noqa: E402  与巡检共用同一套归一化，避免两处漂移

HOME = os.path.expanduser("~")
SYNC_ROOT = os.environ.get("CLAUDE_SYNC_ROOT") or os.path.join(HOME, "workspace")
TRUNK_BRANCHES = ("develop", "main", "master")
SYNC_TREES = ("agents", "rules", "skills", "plans", "tools")
SYNC_FILES = ("settings.json",)
STATE_FILE = ".sync-state.json"
BACKUP_DIR = ".sync-backup"
MAX_DEPTH = 4
SKIP_DIRS = {"node_modules", ".git", "dist", "build", "out", "target", ".venv",
             "vendor", ".gradle", ".idea", ".claude"}


# ---------------------------------------------------------------- 检出发现

def _remote_url_from_config(path):
    """直接读 .git/config 取 origin url，不 fork git。

    本脚本每次会话启动都要扫几十上百个检出，每个起一次 `git config` 子进程要 1 秒以上
    ——这是 hook 里最贵的一步。git config 是 INI 文本，直接解析。
    """
    dot = os.path.join(path, ".git")
    if os.path.isdir(dot):
        cfg = os.path.join(dot, "config")
    elif os.path.isfile(dot):
        # worktree / submodule：.git 是指向真实 gitdir 的文件
        try:
            with open(dot, encoding="utf-8", errors="replace") as f:
                line = f.readline().strip()
        except OSError:
            return ""
        if not line.startswith("gitdir:"):
            return ""
        gd = line.split(":", 1)[1].strip()
        if not os.path.isabs(gd):
            gd = os.path.join(path, gd)
        cfg = os.path.join(gd, "config")
    else:
        return ""
    if not os.path.isfile(cfg):
        return ""
    section = ""
    try:
        with open(cfg, encoding="utf-8", errors="replace") as f:
            for raw in f:
                s = raw.strip()
                if s.startswith("["):
                    section = s.split("]", 1)[0].strip().lower() + "]"
                elif section == '[remote "origin"]' and s.lower().startswith("url"):
                    return s.split("=", 1)[1].strip()
    except (OSError, IndexError):
        return ""
    return ""


def repo_identity(path):
    url = _remote_url_from_config(path)
    if not url:
        try:
            url = subprocess.run(
                ["git", "-C", path, "config", "--get", "remote.origin.url"],
                capture_output=True, text=True, timeout=5).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            url = ""
    return normalize_remote(url)


def current_branch(path):
    """当前分支名。读 .git/HEAD，不 fork git。"""
    dot = os.path.join(path, ".git")
    if os.path.isfile(dot):
        try:
            with open(dot, encoding="utf-8", errors="replace") as f:
                line = f.readline().strip()
        except OSError:
            return ""
        if line.startswith("gitdir:"):
            gd = line.split(":", 1)[1].strip()
            if not os.path.isabs(gd):
                gd = os.path.join(path, gd)
            dot = gd
    head = os.path.join(dot, "HEAD")
    try:
        with open(head, encoding="utf-8", errors="replace") as f:
            ref = f.read().strip()
    except OSError:
        return ""
    return ref.split("refs/heads/", 1)[1] if ref.startswith("ref: refs/heads/") else ""


def discover_peers(root, identity):
    """扫 root 下所有同身份（同 remote）的检出目录。"""
    peers = []
    if not identity or not os.path.isdir(root):
        return peers
    for dirpath, dirnames, _ in os.walk(root):
        if dirpath[len(root):].count(os.sep) >= MAX_DEPTH:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if os.path.exists(os.path.join(dirpath, ".git")) and repo_identity(dirpath) == identity:
            peers.append(dirpath)
    return sorted(peers)


def find_trunk(peers):
    """主干检出：按 $CLAUDE_SYNC_TRUNK 或 develop/main/master 找；都没有就取第一个。"""
    want = [b for b in (os.environ.get("CLAUDE_SYNC_TRUNK"),) + TRUNK_BRANCHES if b]
    branches = {p: current_branch(p) for p in peers}
    for b in want:
        for p in peers:
            if branches[p] == b:
                return p, branches
    return (peers[0] if peers else None), branches


# ---------------------------------------------------------------- 文件与状态

def claude_dir(checkout):
    return os.path.join(checkout, ".claude")


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_files(checkout):
    """该检出 .claude 下参与同步的文件 → {相对路径: 绝对路径}。"""
    base = claude_dir(checkout)
    out = {}
    if not os.path.isdir(base):
        return out
    for tree in SYNC_TREES:
        root = os.path.join(base, tree)
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, files in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != BACKUP_DIR]
            for f in files:
                full = os.path.join(dirpath, f)
                out[os.path.relpath(full, base)] = full
    for name in SYNC_FILES:
        full = os.path.join(base, name)
        if os.path.isfile(full):
            out[name] = full
    return out


def load_state(checkout):
    try:
        with open(os.path.join(claude_dir(checkout), STATE_FILE), encoding="utf-8") as f:
            return json.load(f).get("files", {})
    except (OSError, ValueError):
        return {}


def save_state(checkout, files):
    path = os.path.join(claude_dir(checkout), STATE_FILE)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "files": files}, f, ensure_ascii=False, indent=2, sort_keys=True)
    except OSError:
        pass


def scan(checkout, state):
    """{相对路径: (哈希, 相对上次同步是否动过)}。

    stat 与上次记录一致就直接沿用记录的哈希，不读内容——本脚本每次会话启动都跑，
    全量读文件要 1 秒；稳态下（没动过）应接近零读取。
    """
    out = {}
    for rel, full in iter_files(checkout).items():
        try:
            st = os.stat(full)
        except OSError:
            continue
        prev = state.get(rel)
        if prev and prev[0] == st.st_size and prev[1] == st.st_mtime_ns:
            out[rel] = (prev[2], False)
        else:
            try:
                h = digest(full)
            except OSError:
                continue
            out[rel] = (h, prev is None or prev[2] != h)
    return out


def stat_entry(path):
    st = os.stat(path)
    return [st.st_size, st.st_mtime_ns]


# ---------------------------------------------------------------- 动作

def derealize(checkout, actions):
    """把早先软链方案的残留换成真实副本——同步的前提是各检出都有实体。"""
    base = claude_dir(checkout)

    def one(path):
        if not os.path.islink(path):
            return False
        src = os.path.realpath(path)
        os.remove(path)
        if os.path.isdir(src):
            shutil.copytree(src, path)
        else:
            shutil.copy2(src, path)
        actions.append(f"实体化（原为软链）: {path}")
        return True

    for tree in SYNC_TREES:
        path = os.path.join(base, tree)
        if one(path) or not os.path.isdir(path):
            continue
        for dirpath, _dirnames, files in os.walk(path):
            for f in files:
                one(os.path.join(dirpath, f))
    for name in SYNC_FILES:
        one(os.path.join(base, name))


def copy_in(trunk, target, rel):
    src = os.path.join(claude_dir(trunk), rel)
    dst = os.path.join(claude_dir(target), rel)
    if os.path.isfile(dst):
        # 留一份被盖掉的版本。只有「本地没动过」才会走到这里，正常用不上；
        # 真用上时它是唯一找回途径，所以宁可多存。
        bak = os.path.join(claude_dir(target), BACKUP_DIR, rel)
        os.makedirs(os.path.dirname(bak), exist_ok=True)
        shutil.copy2(dst, bak)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.lexists(dst):
        os.remove(dst)
    # copy2 保留 mtime：同步后 stat 与主干一致，下次会话走快路径
    shutil.copy2(src, dst)


# ---------------------------------------------------------------- 主流程

def sync_into(target, trunk, actions, diverged, status_only=False):
    """把 target 对齐到 trunk：只动 target，且只动「自己没改过」的文件。"""
    if target == trunk:
        return
    state = load_state(target)
    tgt = scan(target, state)
    trk = scan(trunk, load_state(trunk))
    new_state = {}

    for rel in sorted(set(tgt) | set(trk)):
        cur = tgt[rel][0] if rel in tgt else None
        tr = trk[rel][0] if rel in trk else None
        base = state[rel][2] if rel in state else None

        if cur == tr:
            # 已一致（含两边都没有）。记下基线，下次才认得出「本地动没动」。
            if rel in tgt:
                new_state[rel] = stat_entry(os.path.join(claude_dir(target), rel)) + [cur]
            continue

        # 「本地没动过」= 本地根本没有，或内容仍等于上次与主干一致时的基线
        untouched = cur is None or (base is not None and cur == base)

        if untouched:
            if status_only:
                diverged.append((rel, "本地未动，可跟随主干"))
            elif tr is None:
                os.remove(os.path.join(claude_dir(target), rel))
                actions.append((rel, "跟随主干删除"))
            else:
                copy_in(trunk, target, rel)
                actions.append((rel, "跟随主干更新" if cur is not None else "跟随主干新增"))
                new_state[rel] = stat_entry(os.path.join(claude_dir(target), rel)) + [tr]
            continue

        # 本地有改动 → 本分支的工作成果，等合并回主干，不动。
        # 基线必须保持原样：一旦记成本地改动后的内容，下次就会把它当成「没动过」而被主干覆盖。
        diverged.append((rel, "分支独有（等合并回主干）" if tr is None else "本地已改（等合并回主干）"))
        if rel in state:
            new_state[rel] = state[rel]

    if not status_only:
        save_state(target, new_state)
    return new_state


def main(argv):
    quiet = "--quiet" in argv
    status_only = "--status" in argv
    args = [a for a in argv if not a.startswith("--")]
    target = os.path.realpath(
        args[0] if args else os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())

    identity = repo_identity(target)
    if not identity:
        if status_only:
            print(f"{target}: 非 git 检出，跳过")
        return 0

    peers = discover_peers(SYNC_ROOT, identity)
    if target not in peers:
        peers.append(target)
        peers.sort()
    trunk, branches = find_trunk(peers)

    if len(peers) < 2 or trunk is None:
        if status_only:
            print(f"{target}\n  身份: {identity}\n  同仓库检出: 只有它自己（无需同步）")
        return 0

    actions, diverged = [], []
    if not status_only:
        derealize(target, actions)
    sync_into(target, trunk, actions, diverged, status_only)

    if status_only:
        print(f"{target}")
        print(f"  分支: {branches.get(target) or '(detached)'}")
        print(f"  主干: {trunk}  [{branches.get(trunk) or '(detached)'}]")
        print(f"  同仓库检出 {len(peers)} 个：")
        for p in peers:
            mark = " ←主干" if p == trunk else (" ←当前" if p == target else "")
            print(f"    {p}{mark}")
        if diverged:
            print("\n  与主干不同（本分支的改动，完工后合并回主干）：")
            for rel, why in diverged:
                print(f"    {rel}  —  {why}")
        if actions:
            print("\n  可自动跟随主干（本地没动过）：")
            for rel, why in actions:
                print(f"    {rel}  —  {why}")
        if not diverged and not actions:
            print("\n  与主干一致")
        return 0

    if quiet:
        return 0
    for rel, why in actions:
        print(f"  {rel}  —  {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
