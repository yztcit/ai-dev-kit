#!/usr/bin/env python3
"""Personal todo store (todos/items.jsonl) + todo events."""
from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from events import append_event
from memory_paths import ensure_layout, todos_root

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _items_path() -> Path:
    return Path(todos_root()) / "items.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _validate_due(due: str | None) -> str | None:
    if due is None or due == "":
        return None
    if not _DATE_RE.match(due):
        raise ValueError(f"invalid due date (want YYYY-MM-DD): {due}")
    return due


def load_todos() -> list[dict]:
    path = _items_path()
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
        except ValueError:
            continue
    return rows


def _save_todos(items: list[dict]) -> None:
    ensure_layout()
    path = _items_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".jsonl.tmp")
    body = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in items)
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(path)


def add_todo(title: str, due: str | None = None) -> dict:
    title = (title or "").strip()
    if not title:
        raise ValueError("title required")
    due = _validate_due(due)
    row = {
        "id": uuid.uuid4().hex[:12],
        "title": title,
        "due": due,
        "status": "open",
        "created_at": _now_iso(),
    }
    items = load_todos()
    items.append(row)
    _save_todos(items)
    append_event("todo_add", id=row["id"], title=title, due=due)
    return row


def mark_done(todo_id: str) -> dict:
    todo_id = (todo_id or "").strip()
    if not todo_id:
        raise ValueError("id required")
    items = load_todos()
    target = None
    for item in items:
        if str(item.get("id")) == todo_id:
            target = item
            break
    if target is None:
        raise KeyError(f"todo not found: {todo_id}")
    if target.get("status") != "done":
        target["status"] = "done"
        _save_todos(items)
        append_event("todo_done", id=todo_id, title=target.get("title"))
    return target


def list_todos(overdue_only: bool = False) -> list[dict]:
    today = date.today().isoformat()
    out = []
    for item in load_todos():
        if overdue_only:
            if item.get("status") == "done":
                continue
            due = item.get("due")
            if not due or due >= today:
                continue
        out.append(item)
    return out


def cmd_todo(argv):
    """kb todo add|done|list"""
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: kb todo add --title T [--due YYYY-MM-DD]")
        print("       kb todo done <id>")
        print("       kb todo list [--overdue] [--json]")
        return 2 if argv else 0
    sub = argv[0]
    rest = argv[1:]
    if sub == "add":
        title = None
        due = None
        i = 0
        while i < len(rest):
            if rest[i] == "--title" and i + 1 < len(rest):
                title = rest[i + 1]
                i += 2
                continue
            if rest[i] == "--due" and i + 1 < len(rest):
                due = rest[i + 1]
                i += 2
                continue
            i += 1
        if not title:
            print("usage: kb todo add --title T [--due YYYY-MM-DD]")
            return 2
        try:
            row = add_todo(title=title, due=due)
        except ValueError as e:
            print(f"error: {e}")
            return 2
        print(json.dumps(row, ensure_ascii=False, indent=2))
        return 0
    if sub == "done":
        if not rest:
            print("usage: kb todo done <id>")
            return 2
        try:
            row = mark_done(rest[0])
        except KeyError as e:
            print(str(e))
            return 2
        print(json.dumps(row, ensure_ascii=False, indent=2))
        return 0
    if sub == "list":
        overdue_only = "--overdue" in rest
        as_json = "--json" in rest
        rows = list_todos(overdue_only=overdue_only)
        if as_json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
            return 0
        if not rows:
            print("(no todos)")
            return 0
        for row in rows:
            due = row.get("due") or "-"
            print(f"{row.get('id')}\t[{row.get('status')}]\t{due}\t{row.get('title')}")
        return 0
    print(f"unknown todo subcommand: {sub}")
    return 2


if __name__ == "__main__":
    import sys

    raise SystemExit(cmd_todo(sys.argv[1:]))