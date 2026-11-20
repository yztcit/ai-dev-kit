#!/usr/bin/env python3
"""Read-only browse: kb ls / kb show with a unified row format."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from memory_paths import (
    ensure_layout,
    facts_root,
    habits_root,
    methods_personal_root,
    personal_techniques_index_path,
    scratch_root,
    todos_root,
)

TYPES = ("scratch", "technique", "habit", "todo", "facts")
_DEFAULT_LIMIT = 30
_SHOW_MAX_LINES = 80
_SCRATCH_NAME = re.compile(
    r"^(?P<ts>\d{8}-\d{6})-(?P<slug>[a-z0-9-]+)\.md$", re.IGNORECASE
)


def _checkout(explicit: str | None = None) -> str:
    return os.path.realpath(
        explicit or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    )


def _load_json(path: Path) -> dict | list | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _kb_module():
    """Lazy-load engine/kb (same pattern as banner.py)."""
    import importlib.util
    import sys
    from importlib.machinery import SourceFileLoader

    engine = Path(__file__).resolve().parent
    name = "experience_kb_for_browse"
    if name in sys.modules:
        return sys.modules[name]
    if str(engine) not in sys.path:
        sys.path.insert(0, str(engine))
    loader = SourceFileLoader(name, str(engine / "kb"))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    sys.modules[name] = mod
    return mod


def _kb_lookup(checkout: str):
    return _kb_module().lookup(checkout)


def _row(type_: str, id_: str, title: str, meta: str, path: str) -> dict:
    return {
        "type": type_,
        "id": id_,
        "title_or_slug": title,
        "meta": meta,
        "path": path,
    }


def _format_table(rows: list[dict]) -> str:
    if not rows:
        return "(empty)"
    headers = ("type", "id", "title_or_slug", "meta", "path")
    widths = {h: len(h) for h in headers}
    for row in rows:
        for h in headers:
            widths[h] = max(widths[h], len(str(row.get(h) or "")))
    lines = [
        "  ".join(h.ljust(widths[h]) for h in headers),
        "  ".join("-" * widths[h] for h in headers),
    ]
    for row in rows:
        lines.append("  ".join(str(row.get(h) or "").ljust(widths[h]) for h in headers))
    return "\n".join(lines)


def list_scratch(limit: int = _DEFAULT_LIMIT) -> list[dict]:
    ensure_layout()
    root = Path(scratch_root())
    files = sorted(
        (p for p in root.glob("*.md") if p.is_file()),
        key=lambda p: p.name,
        reverse=True,
    )
    rows = []
    for path in files[: max(0, limit)]:
        m = _SCRATCH_NAME.match(path.name)
        if m:
            ts, slug = m.group("ts"), m.group("slug")
            id_ = f"{ts}-{slug}"
            title = slug
            meta = f"ts={ts}"
        else:
            id_ = path.stem
            title = path.stem
            meta = ""
        rows.append(_row("scratch", id_, title, meta, str(path)))
    return rows


def list_technique(limit: int | None = None) -> list[dict]:
    ensure_layout()
    doc = _load_json(Path(personal_techniques_index_path())) or {}
    entries = doc.get("entries") if isinstance(doc, dict) else []
    if not isinstance(entries, list):
        entries = []
    rows = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        tid = str(entry.get("id") or "").strip()
        rel = str(entry.get("path") or "").strip()
        if not tid and rel:
            tid = Path(rel).stem
        strength = entry.get("strength") or ""
        hit = entry.get("hit_count", 0)
        triggers = entry.get("triggers") or []
        title = ""
        if isinstance(triggers, list) and triggers:
            title = ", ".join(str(t) for t in triggers[:3])
        abs_path = rel
        if rel and not os.path.isabs(rel):
            abs_path = str(Path(methods_personal_root()) / rel)
        elif not rel:
            abs_path = str(Path(methods_personal_root()) / f"{tid}.md")
        meta = f"strength={strength} hit={hit}"
        rows.append(_row("technique", tid or Path(abs_path).stem, title, meta, abs_path))
    if limit is not None:
        rows = rows[: max(0, limit)]
    return rows


def list_habit(limit: int | None = None) -> list[dict]:
    from habit_ops import list_habits

    ensure_layout()
    rows = []
    for entry in list_habits():
        hid = str(entry.get("id") or "")
        title = str(entry.get("title") or "")
        rel = str(entry.get("path") or f"{hid}.md")
        path = str(Path(habits_root()) / rel) if not os.path.isabs(rel) else rel
        rows.append(_row("habit", hid, title, "", path))
    if limit is not None:
        rows = rows[: max(0, limit)]
    return rows


def list_todo(limit: int | None = None, overdue_only: bool = False) -> list[dict]:
    from todo_ops import list_todos

    ensure_layout()
    rows = []
    for item in list_todos(overdue_only=overdue_only):
        tid = str(item.get("id") or "")
        title = str(item.get("title") or "")
        due = item.get("due") or ""
        status = item.get("status") or ""
        meta = f"status={status}"
        if due:
            meta += f" due={due}"
        rows.append(
            _row("todo", tid, title, meta, str(Path(todos_root()) / "items.jsonl"))
        )
    if limit is not None:
        rows = rows[: max(0, limit)]
    return rows


def _walk_fact_files(entry_dir: Path, repo_id: str) -> list[dict]:
    rows = []
    if not entry_dir.is_dir():
        return rows
    base = entry_dir / "base"
    if base.is_dir():
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.name in ("kb.yml", ".DS_Store"):
                continue
            rel = path.relative_to(entry_dir).as_posix()
            rows.append(
                _row("facts", rel, path.name, f"repo={repo_id} layer=base", str(path))
            )
    branches = entry_dir / "branches"
    if branches.is_dir():
        for branch_dir in sorted(p for p in branches.iterdir() if p.is_dir()):
            branch = branch_dir.name
            for path in sorted(branch_dir.rglob("*")):
                if not path.is_file() or path.name == ".DS_Store":
                    continue
                rel = path.relative_to(entry_dir).as_posix()
                rows.append(
                    _row(
                        "facts",
                        rel,
                        path.name,
                        f"repo={repo_id} layer=branch branch={branch}",
                        str(path),
                    )
                )
    return rows


def list_facts(
    checkout: str | None = None,
    all_repos: bool = False,
    limit: int | None = None,
) -> list[dict]:
    ensure_layout()
    rows: list[dict] = []
    if all_repos:
        root = Path(facts_root())
        # facts/<host>/<group>/<repo>/
        for host in sorted(p for p in root.iterdir() if p.is_dir()):
            for group in sorted(p for p in host.iterdir() if p.is_dir()):
                for repo in sorted(p for p in group.iterdir() if p.is_dir()):
                    repo_id = f"{host.name}/{group.name}/{repo.name}"
                    rows.extend(_walk_fact_files(repo, repo_id))
    else:
        co = _checkout(checkout)
        key, entry = _kb_lookup(co)
        if not entry:
            return []
        repo_id = key or Path(entry).name
        rows.extend(_walk_fact_files(Path(entry), str(repo_id)))
    if limit is not None:
        rows = rows[: max(0, limit)]
    return rows


def list_type(
    type_: str,
    *,
    limit: int | None = _DEFAULT_LIMIT,
    all_repos: bool = False,
    checkout: str | None = None,
    overdue_only: bool = False,
) -> list[dict]:
    type_ = type_.strip().lower()
    if type_ not in TYPES:
        raise ValueError(f"unknown type: {type_} (want {', '.join(TYPES)})")
    if type_ == "scratch":
        return list_scratch(limit=limit if limit is not None else _DEFAULT_LIMIT)
    if type_ == "technique":
        return list_technique(limit=limit)
    if type_ == "habit":
        return list_habit(limit=limit)
    if type_ == "todo":
        return list_todo(limit=limit, overdue_only=overdue_only)
    return list_facts(checkout=checkout, all_repos=all_repos, limit=limit)


def _resolve_path(type_: str, id_: str, checkout: str | None = None) -> Path:
    id_ = (id_ or "").strip()
    if not id_:
        raise ValueError("id required")
    rows = list_type(
        type_,
        limit=None if type_ != "scratch" else 500,
        all_repos=(type_ == "facts"),
        checkout=checkout,
    )
    # Prefer exact id match; then path suffix; then stem
    for row in rows:
        if row["id"] == id_ or row["path"].endswith(id_) or Path(row["path"]).name == id_:
            return Path(row["path"])
    # Direct path / scratch filename
    if type_ == "scratch":
        p = Path(scratch_root()) / id_
        if not p.suffix:
            # try prefix match
            matches = list(Path(scratch_root()).glob(f"*{id_}*.md"))
            if len(matches) == 1:
                return matches[0]
            if matches:
                raise ValueError(f"ambiguous scratch id: {id_}")
        if p.is_file():
            return p
        p2 = Path(scratch_root()) / f"{id_}.md"
        if p2.is_file():
            return p2
    if type_ == "habit":
        p = Path(habits_root()) / f"{id_}.md"
        if p.is_file():
            return p
    if type_ == "technique":
        p = Path(methods_personal_root()) / f"{id_}.md"
        if p.is_file():
            return p
        # index may store absolute path
        for row in list_technique():
            if row["id"] == id_:
                return Path(row["path"])
    if type_ == "todo":
        raise ValueError("todo has no card file; use kb ls todo (items.jsonl)")
    if type_ == "facts":
        # id is relative path within entry, or absolute
        if os.path.isabs(id_) and Path(id_).is_file():
            return Path(id_)
        co = _checkout(checkout)
        key, entry = _kb_lookup(co)
        if entry:
            p = Path(entry) / id_
            if p.is_file():
                return p
        # search all
        for row in list_facts(all_repos=True):
            if row["id"] == id_ or row["path"].endswith(id_):
                return Path(row["path"])
    raise FileNotFoundError(f"{type_} not found: {id_}")


def show_item(
    type_: str,
    id_: str,
    *,
    full: bool = False,
    checkout: str | None = None,
) -> str:
    type_ = type_.strip().lower()
    if type_ not in TYPES:
        raise ValueError(f"unknown type: {type_}")
    if type_ == "todo":
        from todo_ops import list_todos

        for item in list_todos():
            if str(item.get("id")) == id_:
                return json.dumps(item, ensure_ascii=False, indent=2)
        raise FileNotFoundError(f"todo not found: {id_}")
    path = _resolve_path(type_, id_, checkout=checkout)
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    header = f"# {type_} {id_}\n# path: {path}\n\n"
    if full or len(lines) <= _SHOW_MAX_LINES:
        return header + text
    clipped = "\n".join(lines[:_SHOW_MAX_LINES])
    return (
        header
        + clipped
        + f"\n\n… truncated {len(lines) - _SHOW_MAX_LINES} lines; pass --full for all\n"
    )


def cmd_ls(argv: list[str]) -> int:
    """kb ls <type> [--json] [--limit N] [--all] [--overdue] [checkout]"""
    if not argv or argv[0] in ("-h", "--help"):
        print(
            "usage: kb ls <scratch|technique|habit|todo|facts> "
            "[--json] [--limit N] [--all] [--overdue] [checkout]"
        )
        return 0 if argv else 2
    type_ = argv[0]
    rest = argv[1:]
    as_json = False
    all_repos = False
    overdue_only = False
    limit: int | None = _DEFAULT_LIMIT
    checkout = None
    i = 0
    while i < len(rest):
        a = rest[i]
        if a == "--json":
            as_json = True
        elif a == "--all":
            all_repos = True
        elif a == "--overdue":
            overdue_only = True
        elif a == "--limit" and i + 1 < len(rest):
            limit = int(rest[i + 1])
            i += 1
        elif a == "--full-list":
            limit = None
        elif not a.startswith("--"):
            checkout = a
        else:
            print(f"unknown flag: {a}")
            return 2
        i += 1
    if type_ in ("habit", "todo", "technique", "facts") and "--limit" not in rest:
        # small stores + current-repo facts: show all unless --limit set
        if limit == _DEFAULT_LIMIT:
            limit = None
    try:
        if type_ == "facts" and not all_repos:
            co = _checkout(checkout)
            key, entry = _kb_lookup(co)
            if not entry:
                print(
                    f"当前检出未登记到 KB: {co}\n"
                    "可: kb import <目录>  或  kb ls facts --all"
                )
                return 1
        rows = list_type(
            type_,
            limit=limit,
            all_repos=all_repos,
            checkout=checkout,
            overdue_only=overdue_only,
        )
    except ValueError as exc:
        print(exc)
        return 2
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(_format_table(rows))
        print(f"\n({len(rows)} row(s))")
    return 0


def cmd_show(argv: list[str]) -> int:
    """kb show <type> <id> [--full] [--json] [checkout]"""
    if len(argv) < 2 or argv[0] in ("-h", "--help"):
        print("usage: kb show <scratch|technique|habit|todo|facts> <id> [--full] [checkout]")
        return 0 if argv and argv[0] in ("-h", "--help") else 2
    type_, id_ = argv[0], argv[1]
    rest = argv[2:]
    full = False
    checkout = None
    for a in rest:
        if a == "--full":
            full = True
        elif not a.startswith("--"):
            checkout = a
        else:
            print(f"unknown flag: {a}")
            return 2
    try:
        text = show_item(type_, id_, full=full, checkout=checkout)
    except (ValueError, FileNotFoundError) as exc:
        print(exc)
        return 1
    print(text)
    return 0
