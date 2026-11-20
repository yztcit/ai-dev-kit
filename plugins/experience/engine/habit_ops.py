#!/usr/bin/env python3
"""Cross-repo personal habits (habits/<id>.md + index.json)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from events import append_event
from memory_paths import ensure_layout, habits_index_path, habits_root

_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


def _load_index() -> dict:
    path = Path(habits_index_path())
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass
    return {"schema": 1, "entries": []}


def _save_index(data: dict) -> None:
    ensure_layout()
    path = Path(habits_index_path())
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _habit_card(habit_id: str, title: str, body: str) -> str:
    body = (body or "").rstrip() + "\n"
    return (
        "---\n"
        f"id: {habit_id}\n"
        f"title: {title}\n"
        "---\n\n"
        f"{body}"
    )


def _validate_id(habit_id: str) -> str:
    habit_id = (habit_id or "").strip()
    if not habit_id or not _ID_RE.match(habit_id):
        raise ValueError("invalid --id (use letters, digits, _ -)")
    return habit_id


def upsert_habit(habit_id: str, title: str, body: str) -> dict:
    habit_id = _validate_id(habit_id)
    title = (title or "").strip()
    if not title:
        raise ValueError("title required")
    ensure_layout()
    rel = f"{habit_id}.md"
    card_path = Path(habits_root()) / rel
    card_path.write_text(_habit_card(habit_id, title, body), encoding="utf-8")
    abs_path = str(card_path.resolve())
    data = _load_index()
    entries = [e for e in data.get("entries", []) if isinstance(e, dict)]
    row = {"id": habit_id, "path": rel, "title": title}
    for i, entry in enumerate(entries):
        if str(entry.get("id") or "") == habit_id:
            entries[i] = row
            break
    else:
        entries.append(row)
    data["schema"] = 1
    data["entries"] = entries
    _save_index(data)
    event = append_event("habit_upsert", id=habit_id, title=title, path=rel)
    return {"id": habit_id, "title": title, "path": abs_path, "event": event}


def list_habits() -> list[dict]:
    data = _load_index()
    return [e for e in data.get("entries", []) if isinstance(e, dict)]


def cmd_habit(argv):
    """kb habit upsert|list"""
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: kb habit upsert --id ID --title T --body TEXT")
        print("       kb habit upsert --id ID --title T --body-file F")
        print("       kb habit list [--json]")
        return 2 if argv else 0
    sub = argv[0]
    rest = argv[1:]
    if sub == "upsert":
        habit_id = None
        title = None
        body = None
        body_file = None
        i = 0
        while i < len(rest):
            if rest[i] == "--id" and i + 1 < len(rest):
                habit_id = rest[i + 1]
                i += 2
                continue
            if rest[i] == "--title" and i + 1 < len(rest):
                title = rest[i + 1]
                i += 2
                continue
            if rest[i] == "--body" and i + 1 < len(rest):
                body = rest[i + 1]
                i += 2
                continue
            if rest[i] == "--body-file" and i + 1 < len(rest):
                body_file = rest[i + 1]
                i += 2
                continue
            i += 1
        if body_file:
            try:
                body = Path(body_file).read_text(encoding="utf-8")
            except OSError as e:
                print(f"cannot read --body-file: {e}")
                return 2
        if not habit_id or not title or body is None:
            print("usage: kb habit upsert --id ID --title T --body TEXT")
            print("       kb habit upsert --id ID --title T --body-file F")
            return 2
        try:
            result = upsert_habit(habit_id=habit_id, title=title, body=body)
        except ValueError as e:
            print(f"error: {e}")
            return 2
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if sub == "list":
        as_json = "--json" in rest
        rows = list_habits()
        if as_json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
            return 0
        if not rows:
            print("(no habits)")
            return 0
        for row in rows:
            print(f"{row.get('id')}\t{row.get('title')}\t{row.get('path')}")
        return 0
    print(f"unknown habit subcommand: {sub}")
    return 2


if __name__ == "__main__":
    import sys

    raise SystemExit(cmd_habit(sys.argv[1:]))