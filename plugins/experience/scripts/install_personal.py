#!/usr/bin/env python3
"""Idempotent personal-edition install for this Mac + Claude Code."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
ENGINE = PLUGIN_ROOT / "engine"
sys.path.insert(0, str(ENGINE))

from bootstrap_seeds import ensure_seed_techniques  # noqa: E402
from doctor import run_doctor  # noqa: E402
from memory_paths import (  # noqa: E402
    PRODUCT_VERSION,
    ensure_layout,
    install_marker_path,
)


def _settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def _link_or_replace(dest: Path, target: Path) -> bool:
    """Symlink dest → target if missing or pointing elsewhere. Returns True if updated."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    target = target.resolve()
    if dest.is_symlink() or dest.exists():
        try:
            if dest.resolve() == target:
                return False
        except OSError:
            pass
        dest.unlink()
    dest.symlink_to(target)
    return True


def _ensure_command_links() -> int:
    """Project commands/kb-*.md into Cursor and Claude command dirs."""
    src_dir = PLUGIN_ROOT / "commands"
    if not src_dir.is_dir():
        return 0
    updated = 0
    targets = (
        Path.home() / ".cursor" / "commands",
        Path.home() / ".claude" / "commands",
    )
    for src in sorted(src_dir.glob("kb-*.md")):
        for root in targets:
            if _link_or_replace(root / src.name, src):
                updated += 1
    return updated


def _remove_capture_skill_links() -> int:
    """Slash 入口只保留 commands；卸掉用户 skills 里的 capture 项，避免 /note 与 /kb-note 双开。

    插件内 skills/kb-* 仍作详细剧本（marketplace / 读源码），个人版不链到 ~/.claude/skills。
    shared-config 等其它 skill 不动。
    """
    skills_root = Path.home() / ".claude" / "skills"
    if not skills_root.is_dir():
        return 0
    removed = 0
    for name in ("note", "deposit", "habit", "kb-note", "kb-deposit", "kb-habit"):
        dest_dir = skills_root / name
        link = dest_dir / "SKILL.md"
        if link.is_symlink() or link.exists():
            try:
                link.unlink()
                removed += 1
            except OSError:
                pass
        if dest_dir.is_dir():
            try:
                # only remove empty leftover dirs we created for capture skills
                if not any(dest_dir.iterdir()):
                    dest_dir.rmdir()
            except OSError:
                pass
    return removed


def _experience_hook_cmd(script_name: str) -> str:
    path = PLUGIN_ROOT / "hooks" / script_name
    return f'bash "{path}"'


def _is_experience_cmd(cmd: str) -> bool:
    return "plugins/experience/hooks/" in cmd and (
        "session_start.sh" in cmd or "prompt_hit.sh" in cmd
    )


def _ensure_hooks(settings: dict) -> bool:
    """Ensure experience SessionStart + UserPromptSubmit exist. Returns True if changed."""
    changed = False
    hooks = settings.setdefault("hooks", {})

    def ensure_event(event_name: str, script: str, timeout=None):
        nonlocal changed
        groups = hooks.setdefault(event_name, [])
        if not isinstance(groups, list):
            hooks[event_name] = []
            groups = hooks[event_name]
        want = _experience_hook_cmd(script)
        found = False
        for group in groups:
            for hook in (group or {}).get("hooks") or []:
                cmd = (hook or {}).get("command") or ""
                if _is_experience_cmd(cmd):
                    found = True
                    if cmd != want:
                        hook["command"] = want
                        if timeout is not None:
                            hook["timeout"] = timeout
                        changed = True
                    elif timeout is not None and hook.get("timeout") != timeout:
                        hook["timeout"] = timeout
                        changed = True
        if not found:
            entry = {"type": "command", "command": want}
            if timeout is not None:
                entry["timeout"] = timeout
            groups.insert(0, {"hooks": [entry]})
            changed = True

    ensure_event("SessionStart", "session_start.sh")
    ensure_event("UserPromptSubmit", "prompt_hit.sh", timeout=15)
    return changed


def _write_marker():
    payload = {
        "version": PRODUCT_VERSION,
        "installed_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "plugin_root": str(PLUGIN_ROOT),
        "product": "experience-personal",
    }
    Path(install_marker_path()).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main():
    ensure_layout()
    copied = ensure_seed_techniques(PLUGIN_ROOT)
    skills_removed = _remove_capture_skill_links()
    commands_linked = _ensure_command_links()

    settings_file = _settings_path()
    if settings_file.is_file():
        settings = json.loads(settings_file.read_text(encoding="utf-8"))
    else:
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings = {}

    hooks_changed = _ensure_hooks(settings)
    if hooks_changed:
        tmp = settings_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(settings_file)

    _write_marker()
    result = run_doctor(PLUGIN_ROOT)

    print(f"experience personal install · v{PRODUCT_VERSION}")
    print(f"  plugin: {PLUGIN_ROOT}")
    print(f"  seeds_copied: {copied}")
    print(f"  capture_skills_unlinked: {skills_removed}")
    print(f"  commands_linked: {commands_linked}")
    print(f"  hooks_updated: {hooks_changed}")
    print(f"  doctor: {'OK' if result['ok'] else 'NEEDS_FIX'}")
    if not result["ok"]:
        for c in result["checks"]:
            if not c["ok"]:
                print(f"    ✗ {c['name']}: {c['detail']}")
        return 1
    print("  daily: 记一下 / 沉淀；查反馈: python3 engine/kb report")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
