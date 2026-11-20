#!/usr/bin/env python3
"""Scratch note capture + note events for personal experience."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from events import append_event
from memory_paths import ensure_layout, scratch_root


def _sanitize_slug(slug: str) -> str:
    raw = (slug or "").strip().lower()
    raw = re.sub(r"[^a-z0-9-]+", "-", raw)
    raw = re.sub(r"-+", "-", raw).strip("-")
    return raw or "note"


def _scratch_filename(slug: str) -> str:
    ts = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    return f"{ts}-{_sanitize_slug(slug)}.md"


def write_note(slug: str, body: str) -> dict:
    """Write body to scratch/<timestamp>-<slug>.md and append event type note."""
    ensure_layout()
    clean_slug = _sanitize_slug(slug)
    root = Path(scratch_root())
    path = root / _scratch_filename(clean_slug)
    path.write_text(body or "", encoding="utf-8")
    row = append_event("note", path=str(path.resolve()), slug=clean_slug)
    return {"path": str(path.resolve()), "slug": clean_slug, "event": row}


def cmd_note(argv):
    """kb note --slug S (--body-file F | --body TEXT)"""
    slug = None
    body = None
    body_file = None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--slug" and i + 1 < len(argv):
            slug = argv[i + 1]
            i += 2
            continue
        if arg == "--body" and i + 1 < len(argv):
            body = argv[i + 1]
            i += 2
            continue
        if arg == "--body-file" and i + 1 < len(argv):
            body_file = argv[i + 1]
            i += 2
            continue
        if arg in ("-h", "--help"):
            print("usage: kb note --slug S --body-file F")
            print("       kb note --slug S --body TEXT")
            return 0
        i += 1
    if not slug:
        print("usage: kb note --slug S --body-file F")
        print("       kb note --slug S --body TEXT")
        return 2
    if body_file:
        try:
            body = Path(body_file).read_text(encoding="utf-8")
        except OSError as e:
            print(f"cannot read --body-file: {e}")
            return 2
    if body is None:
        print("error: require --body-file or --body")
        return 2
    result = write_note(slug=slug, body=body)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(cmd_note(sys.argv[1:]))