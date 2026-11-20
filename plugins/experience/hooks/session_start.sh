#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENGINE_DIR="${PLUGIN_DIR}/engine"

python3 - "${ENGINE_DIR}" "${PLUGIN_DIR}" <<'PY'
import importlib.util
import os
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path


def load_module(name, path, extra_sys_path=None):
    if extra_sys_path:
        sys.path.insert(0, str(extra_sys_path))
    try:
        loader = SourceFileLoader(name, str(path))
        spec = importlib.util.spec_from_loader(name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        return module
    finally:
        if extra_sys_path:
            sys.path.remove(str(extra_sys_path))


def print_unregistered_hint(repo_key, checkout, engine_dir, memory_index):
    print(f"[experience] 当前仓库未接入 KB: {repo_key}")
    print(f"  1. import：python3 {engine_dir / 'kb'} import \"{checkout}\"")
    print("  2. 跳过：本次忽略即可，继续当前会话")
    print(f"  3. 永不提醒：将 \"{repo_key}\" 加入 {memory_index} 的 never_remind")


def maybe_print_personal_fact(kb, entry_dir, branch, config):
    if (config.get("overlay") or "").strip().lower() != "team-tracked":
        return
    candidates = []
    if branch:
        candidates.append(Path(entry_dir) / "branches" / branch / "PERSONAL.md")
    candidates.append(Path(entry_dir) / "base" / "PERSONAL.md")
    for candidate in candidates:
        if candidate.is_file():
            print(f"[personal-fact] team-tracked 仓检测到个人补充事实，可按需读入: {candidate}")
            return


def maybe_print_techniques(hit):
    count = hit.count_personal_entries(allowed_strengths=("repeated", "used"))
    if count <= 0:
        return
    print(f"[technique] 已有 {count} 张个人技巧卡可按需调用。")


def maybe_run_fallback(kb, engine_dir):
    fallback = os.environ.get("KB_FALLBACK_SYNC", kb.DEFAULT_FALLBACK)
    if os.path.isfile(fallback):
        subprocess.run([sys.executable, fallback], check=False)


def main():
    engine_dir = Path(sys.argv[1]).resolve()
    plugin_dir = Path(sys.argv[2]).resolve()
    checkout = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())

    memory_paths = load_module("experience_memory_paths", engine_dir / "memory_paths.py", extra_sys_path=engine_dir)
    kb = load_module("experience_kb", engine_dir / "kb", extra_sys_path=engine_dir)
    hit = load_module("experience_hit_techniques", engine_dir / "hit_techniques.py", extra_sys_path=engine_dir)
    bootstrap = load_module("experience_bootstrap_seeds", engine_dir / "bootstrap_seeds.py", extra_sys_path=engine_dir)

    memory_paths.ensure_layout()
    bootstrap.ensure_seed_techniques(plugin_dir)
    events = load_module("experience_events", engine_dir / "events.py", extra_sys_path=engine_dir)
    code, lines = kb.sync(checkout, quiet=True)
    for line in lines:
        print(line)

    repo_key = kb.repo_identity(checkout)
    if code == 3:
        maybe_run_fallback(kb, engine_dir)
        index_doc = kb.load_index_doc()
        never_remind = set(index_doc.get("never_remind", [])) if isinstance(index_doc, dict) else set()
        if repo_key and repo_key not in never_remind:
            print_unregistered_hint(repo_key, checkout, engine_dir, memory_paths.index_path())
        try:
            events.append_event(
                "session_start",
                checkout=checkout,
                repo=repo_key or "",
                registered=False,
            )
        except Exception:
            pass
        return 0

    if not repo_key:
        try:
            events.append_event("session_start", checkout=checkout, repo="", registered=False)
        except Exception:
            pass
        return 0
    _key, entry_dir = kb.lookup(checkout)
    if not entry_dir:
        return 0
    branch = kb.current_branch(checkout)
    config = kb.parse_kb_yml(os.path.join(entry_dir, "kb.yml"))
    maybe_print_personal_fact(kb, entry_dir, branch, config)
    maybe_print_techniques(hit)
    try:
        events.append_event(
            "session_start",
            checkout=checkout,
            repo=repo_key,
            registered=True,
            branch=branch or "",
            overlay=(config.get("overlay") or ""),
        )
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ experience SessionStart 失败（不影响使用）：{type(exc).__name__}: {exc}")
        raise SystemExit(0)
PY
