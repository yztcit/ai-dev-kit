#!/usr/bin/env python3
"""Personal-edition health check — one command before daily use."""
from __future__ import annotations

import json
import os
from pathlib import Path

from memory_paths import (
    PRODUCT_VERSION,
    ensure_layout,
    events_path,
    facts_root,
    index_path,
    install_marker_path,
    methods_personal_root,
    personal_techniques_index_path,
    scratch_root,
)
from state_ops import is_enabled


DEFAULT_PLUGIN = Path.home() / "workspace" / "AI-dev-kit" / "plugins" / "experience"


def _plugin_root():
    env = os.environ.get("EXPERIENCE_PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        return Path(env).resolve()
    return DEFAULT_PLUGIN.resolve()


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _settings_path():
    return Path.home() / ".claude" / "settings.json"


def _hook_commands(settings: dict) -> list[str]:
    cmds = []
    hooks = (settings or {}).get("hooks") or {}
    for _name, groups in hooks.items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            for hook in (group or {}).get("hooks") or []:
                cmd = (hook or {}).get("command")
                if isinstance(cmd, str):
                    cmds.append(cmd)
    return cmds


def _skill_ok(name: str) -> tuple[bool, str]:
    link = Path.home() / ".claude" / "skills" / name / "SKILL.md"
    if not link.exists():
        return False, f"missing ~/.claude/skills/{name}/SKILL.md"
    target = link.resolve() if link.is_symlink() or link.exists() else None
    if target and target.is_file():
        return True, str(target)
    return False, f"broken skill link: {link}"


def run_doctor(plugin_dir: Path | None = None) -> dict:
    plugin = Path(plugin_dir or _plugin_root()).resolve()
    ensure_layout()
    checks = []

    def add(ok: bool, name: str, detail: str):
        checks.append({"ok": ok, "name": name, "detail": detail})

    add(plugin.is_dir(), "plugin_root", str(plugin))
    session = plugin / "hooks" / "session_start.sh"
    prompt = plugin / "hooks" / "prompt_hit.sh"
    add(session.is_file(), "session_start_hook", str(session))
    add(prompt.is_file(), "prompt_hit_hook", str(prompt))

    kb_on = is_enabled()
    if kb_on:
        add(True, "kb_enabled", "ON")
    else:
        add(True, "kb_enabled", "DISABLED")
    add(Path(facts_root()).is_dir(), "facts_dir", facts_root())
    add(Path(methods_personal_root()).is_dir(), "methods_personal", methods_personal_root())
    add(Path(scratch_root()).is_dir(), "scratch", scratch_root())
    add(Path(events_path()).parent.is_dir(), "logs_dir", str(Path(events_path()).parent))

    idx = _load_json(Path(index_path())) or {}
    entries = idx.get("entries") if isinstance(idx, dict) else {}
    add(isinstance(entries, dict), "memory_index", f"{len(entries or {})} repo(s) registered")

    pidx = _load_json(Path(personal_techniques_index_path())) or {}
    techniques = pidx.get("entries") if isinstance(pidx, dict) else []
    n_tech = len(techniques or [])
    add(n_tech > 0, "personal_techniques", f"{n_tech} card(s)")

    settings_file = _settings_path()
    settings = _load_json(settings_file) if settings_file.is_file() else None
    if not settings:
        add(False, "claude_settings", f"missing or invalid {settings_file}")
    else:
        cmds = _hook_commands(settings)
        has_session = any("session_start.sh" in c and "experience" in c for c in cmds)
        has_prompt = any("prompt_hit.sh" in c and "experience" in c for c in cmds)
        # also accept absolute path to this plugin even without substring experience in odd installs
        if not has_session:
            has_session = any(str(session) in c for c in cmds)
        if not has_prompt:
            has_prompt = any(str(prompt) in c for c in cmds)
        add(has_session, "claude_session_hook", "SessionStart → experience session_start.sh")
        add(has_prompt, "claude_prompt_hook", "UserPromptSubmit → experience prompt_hit.sh")

    note_ok, note_detail = _skill_ok("note")
    deposit_ok, deposit_detail = _skill_ok("deposit")
    add(note_ok, "skill_note", note_detail)
    add(deposit_ok, "skill_deposit", deposit_detail)

    marker = _load_json(Path(install_marker_path()))
    if marker:
        add(True, "install_marker", f"version={marker.get('version')} at {marker.get('installed_at')}")
    else:
        add(False, "install_marker", "run install_personal.py once")

    events_file = Path(events_path())
    event_lines = 0
    if events_file.is_file():
        event_lines = sum(1 for line in events_file.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())
    add(True, "events_log", f"{event_lines} line(s) in {events_file}")

    failed = [c for c in checks if not c["ok"]]
    if not kb_on:
        overall_ok = True
        status = "DISABLED"
    else:
        overall_ok = len(failed) == 0
        status = "OK" if overall_ok else "NEEDS_FIX"
    return {
        "product_version": PRODUCT_VERSION,
        "ok": overall_ok,
        "status": status,
        "kb_enabled": kb_on,
        "failed": [c["name"] for c in failed],
        "checks": checks,
        "plugin_root": str(plugin),
    }


def cmd_doctor(argv):
    as_json = "--json" in argv
    plugin = None
    if "--plugin" in argv:
        i = argv.index("--plugin")
        if i + 1 < len(argv):
            plugin = Path(argv[i + 1])
    result = run_doctor(plugin)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = result.get("status") or ("OK" if result["ok"] else "NEEDS_FIX")
        print(f"experience doctor · personal {result['product_version']} · {status}")
        if status == "DISABLED":
            print("  kb 当前关闭 — hooks 不注入；`kb on` 恢复")
        for c in result["checks"]:
            mark = "✓" if c["ok"] else "✗"
            extra = ""
            if c["name"] == "kb_enabled" and c["detail"] == "DISABLED":
                extra = " (注入已关闭)"
            print(f"  {mark} {c['name']}: {c['detail']}{extra}")
        if not result["ok"] and status != "DISABLED":
            print("fix: bash plugins/experience/scripts/install_personal.sh")
            return 1
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    import sys

    raise SystemExit(cmd_doctor(sys.argv[1:]))
