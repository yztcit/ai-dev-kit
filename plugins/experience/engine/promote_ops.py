#!/usr/bin/env python3
"""Promote personal techniques to plugin inbox-promote for shareable review."""
from __future__ import annotations

import json
import re
from pathlib import Path

from events import append_event
from memory_paths import ensure_layout, methods_personal_root

_STRENGTH_RE = re.compile(r"^strength:\s*(\S+)", re.MULTILINE)


def _plugin_root() -> Path:
    from doctor import _plugin_root as root_fn

    return root_fn()


def _load_index() -> dict:
    from memory_paths import personal_techniques_index_path

    path = Path(personal_techniques_index_path())
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass
    return {"schema": 1, "entries": []}


def _match_entry(entry: dict, needle: str) -> bool:
    needle = (needle or "").strip()
    if not needle:
        return False
    path = str(entry.get("path") or "")
    eid = str(entry.get("id") or "")
    name = Path(path).name
    return needle in (path, eid, name) or path.endswith(needle) or name == needle


def _resolve_card_path(path_str: str) -> Path | None:
    if not path_str:
        return None
    raw = Path(path_str)
    if raw.is_file():
        return raw.resolve()
    cand = Path(methods_personal_root()) / raw.name
    if cand.is_file():
        return cand.resolve()
    cand = Path(methods_personal_root()) / path_str
    if cand.is_file():
        return cand.resolve()
    return None


def _strength_from_frontmatter(card_path: Path) -> str | None:
    try:
        text = card_path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = _STRENGTH_RE.search(text)
    return m.group(1).strip().lower() if m else None


def _effective_strength(entry: dict | None, card_path: Path | None) -> str | None:
    if entry:
        s = str(entry.get("strength") or "").strip().lower()
        if s:
            return s
    if card_path:
        return _strength_from_frontmatter(card_path)
    return None


def promote_technique(id_or_path: str, plugin_root: str | Path | None = None) -> dict:
    """Copy a personal technique card to inbox-promote/<id>.md and append promote event."""
    ensure_layout()
    needle = (id_or_path or "").strip()
    if not needle:
        raise SystemExit("promote requires id or path")

    data = _load_index()
    entries = [e for e in data.get("entries", []) if isinstance(e, dict)]
    entry = None
    for row in entries:
        if _match_entry(row, needle):
            entry = row
            break

    card_path = None
    if entry:
        card_path = _resolve_card_path(str(entry.get("path") or ""))
    if card_path is None:
        card_path = _resolve_card_path(needle)
        if card_path is None and not needle.endswith(".md"):
            card_path = _resolve_card_path(f"{needle}.md")

    if card_path is None:
        raise SystemExit(f"technique card not found: {needle}")

    strength = _effective_strength(entry, card_path)
    if strength not in ("used", "repeated"):
        raise SystemExit(
            f"technique strength must be used or repeated (index or frontmatter); got: {strength or '(missing)'}"
        )

    technique_id = str(entry.get("id") if entry else "") or card_path.stem
    plugin = Path(plugin_root or _plugin_root()).resolve()
    inbox = plugin / "inbox-promote"
    inbox.mkdir(parents=True, exist_ok=True)
    dest = inbox / f"{technique_id}.md"
    dest.write_text(card_path.read_text(encoding="utf-8"), encoding="utf-8")

    rel_dest = f"inbox-promote/{technique_id}.md"
    row = append_event(
        "promote",
        id=technique_id,
        path=rel_dest,
        source=str(card_path),
        strength=strength,
    )
    return {
        "id": technique_id,
        "dest": str(dest.resolve()),
        "path": rel_dest,
        "strength": strength,
        "event": row,
    }