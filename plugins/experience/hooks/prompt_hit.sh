#!/usr/bin/env bash
# UserPromptSubmit: match techniques and inject via hookSpecificOutput.additionalContext.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENGINE_DIR="${PLUGIN_DIR}/engine"

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


def card_body(path):
    text = Path(path).read_text(encoding="utf-8")
    # Strip YAML frontmatter for the injected reminder (keep readable body).
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        end = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end = i
                break
        if end is not None:
            text = "\n".join(lines[end + 1 :]).strip()
    # Keep under typical hook field budget with headroom for wrapper text.
    max_body = 7000
    if len(text) > max_body:
        text = text[:max_body] + "\n…(truncated)"
    return text


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

    paths = hit.match_index(prompt, allowed_strengths=None, limit=3)
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

    blocks = []
    resolved_paths = []
    strengths = []
    for rel in paths:
        entry = by_path.get(rel) or by_path.get(Path(rel).name) or {}
        strength = (entry.get("strength") or "hypothesis").strip().lower()
        card = resolve_card(rel, personal_dir, techniques_dir, seed_dir)
        if card is None:
            continue
        label = "hypothesis/unverified" if strength == "hypothesis" else strength
        body = card_body(card)
        blocks.append(
            "Matched experience technique (%s): %s\n\n%s"
            % (label, card, body)
        )
        resolved_paths.append(str(card))
        strengths.append(strength)

    if not blocks:
        return

    # Ops log + hit_count for personal feedback (never print to hook stdout).
    try:
        events = load_module(
            "experience_events",
            engine_dir / "events.py",
            extra_sys_path=engine_dir,
        )
        technique_ops = load_module(
            "experience_technique_ops",
            engine_dir / "technique_ops.py",
            extra_sys_path=engine_dir,
        )
        fp = events.prompt_fingerprint(prompt)
        checkout = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
        events.append_event(
            "technique_hit",
            checkout=checkout,
            paths=resolved_paths,
            strengths=strengths,
            **fp,
        )
        technique_ops.record_hits(resolved_paths)
    except Exception:
        pass

    # Factual reminder (not imperative "system command") so Claude uses it rather
    # than treating it as prompt injection. Authority is the experience card.
    context = (
        "Experience technique match for this user message. "
        "Authoritative source for this method is the experience technique card "
        "under ~/.local/share/dev-memory/methods-personal (or bundled techniques). "
        "Project auto-memory files with similar wording are secondary echoes, "
        "not the source of truth, and this turn does not require re-saving the "
        "same discipline into project MEMORY.\n\n"
        + "\n\n-----\n\n".join(blocks)
    )

    # Only JSON on stdout — required for UserPromptSubmit structured injection.
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": context,
                }
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
PY
