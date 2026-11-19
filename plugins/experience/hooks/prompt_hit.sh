#!/usr/bin/env bash
# UserPromptSubmit: match techniques against the user prompt and inject hints.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENGINE_DIR="${PLUGIN_DIR}/engine"

# Claude feeds JSON on stdin; capture BEFORE starting python (heredoc would steal it).
INPUT="$(cat || true)"

EXPERIENCE_PROMPT_JSON="$INPUT" python3 - "$ENGINE_DIR" "$PLUGIN_DIR" <<'PY'
import importlib.util
import json
import os
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
        if extra_sys_path and str(extra_sys_path) in sys.path:
            sys.path.remove(str(extra_sys_path))


def extract_prompt(raw):
    raw = (raw or "").strip()
    if not raw:
        return ""
    try:
        data = json.loads(raw)
    except ValueError:
        return raw
    if isinstance(data, str):
        return data
    if not isinstance(data, dict):
        return raw
    for key in ("prompt", "user_prompt", "message", "text", "content"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val
    for key in ("input", "payload", "data"):
        nested = data.get(key)
        if isinstance(nested, dict):
            for k in ("prompt", "user_prompt", "message", "text"):
                val = nested.get(k)
                if isinstance(val, str) and val.strip():
                    return val
    return ""


def resolve_card(path_str, personal_dir, techniques_dir, seed_dir):
    p = Path(path_str)
    if p.is_file():
        return p
    name = p.name
    for base in (personal_dir, techniques_dir, seed_dir):
        for cand in (base / name, base / path_str):
            if cand.is_file():
                return cand
    return None


def main():
    engine_dir = Path(sys.argv[1]).resolve()
    plugin_dir = Path(sys.argv[2]).resolve()
    prompt = extract_prompt(os.environ.get("EXPERIENCE_PROMPT_JSON", ""))
    if not prompt.strip():
        return

    hit = load_module(
        "experience_hit_techniques",
        engine_dir / "hit_techniques.py",
        extra_sys_path=engine_dir,
    )
    memory_paths = load_module(
        "experience_memory_paths",
        engine_dir / "memory_paths.py",
        extra_sys_path=engine_dir,
    )
    memory_paths.ensure_layout()

    paths = hit.match_index(prompt, allowed_strengths=None, limit=5)
    if not paths:
        return

    personal_dir = Path(memory_paths.methods_personal_root())
    techniques_dir = plugin_dir / "techniques"
    seed_dir = plugin_dir / "seed_techniques"
    by_path = {}
    for entry in hit.normalize_entries(hit.load_index()):
        rel = str(entry.get("path") or "").strip()
        if not rel:
            continue
        by_path[rel] = entry
        by_path[Path(rel).name] = entry

    print(
        "[experience-technique] 以下技巧卡与当前话术触发匹配；"
        "请优先 Read 后按卡执行（勿仅引用项目 MEMORY）："
    )
    for rel in paths:
        entry = by_path.get(rel) or by_path.get(Path(rel).name) or {}
        strength = (entry.get("strength") or "hypothesis").strip().lower()
        card = resolve_card(rel, personal_dir, techniques_dir, seed_dir)
        label = "未验证假设" if strength == "hypothesis" else strength
        if card is None:
            print("  - (%s) %s （文件未找到）" % (label, rel))
            continue
        print("  - (%s) %s" % (label, card))


if __name__ == "__main__":
    main()
PY
