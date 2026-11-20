#!/usr/bin/env python3
"""Personal technique index ops: hit_count + strength bump."""
from __future__ import annotations

import json
from pathlib import Path

from events import append_event
from memory_paths import ensure_layout, personal_techniques_index_path

STRENGTH_ORDER = ["hypothesis", "used", "repeated", "contradicted"]


def _load():
    path = Path(personal_techniques_index_path())
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass
    return {"schema": 1, "entries": []}


def _save(data):
    ensure_layout()
    path = Path(personal_techniques_index_path())
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _match_entry(entry: dict, needle: str) -> bool:
    needle = (needle or "").strip()
    if not needle:
        return False
    path = str(entry.get("path") or "")
    eid = str(entry.get("id") or "")
    name = Path(path).name
    return needle in (path, eid, name) or path.endswith(needle) or name == needle


def record_hits(paths: list[str]) -> int:
    """Increment hit_count on personal index entries that match paths. Returns updated count."""
    if not paths:
        return 0
    data = _load()
    entries = [e for e in data.get("entries", []) if isinstance(e, dict)]
    updated = 0
    needles = set()
    for p in paths:
        needles.add(str(p))
        needles.add(Path(p).name)
    for entry in entries:
        path = str(entry.get("path") or "")
        name = Path(path).name
        if path in needles or name in needles:
            entry["hit_count"] = int(entry.get("hit_count") or 0) + 1
            updated += 1
    if updated:
        data["entries"] = entries
        _save(data)
    return updated


def bump_strength(needle: str, to: str | None = None) -> dict:
    data = _load()
    entries = [e for e in data.get("entries", []) if isinstance(e, dict)]
    target = None
    for entry in entries:
        if _match_entry(entry, needle):
            target = entry
            break
    if target is None:
        raise SystemExit(f"technique not found in personal index: {needle}")

    current = (target.get("strength") or "hypothesis").strip().lower()
    if to:
        new = to.strip().lower()
    else:
        if current == "hypothesis":
            new = "used"
        elif current == "used":
            new = "repeated"
        else:
            new = current
    if new not in STRENGTH_ORDER:
        raise SystemExit(f"invalid strength: {new}")
    if new in ("used", "repeated"):
        # anti-example required by design — warn only; caller/skill enforces
        pass
    old = current
    target["strength"] = new
    data["entries"] = entries
    _save(data)
    # keep card frontmatter in sync when path is a real file under methods-personal
    _sync_card_strength(str(target.get("path") or ""), new)
    row = append_event(
        "technique_bump",
        path=str(target.get("path") or ""),
        id=str(target.get("id") or ""),
        from_strength=old,
        to_strength=new,
    )
    return {"path": target.get("path"), "from": old, "to": new, "event": row}


def _sync_card_strength(path_str: str, strength: str):
    path = Path(path_str)
    if not path.is_file():
        # relative name under methods-personal
        from memory_paths import methods_personal_root

        cand = Path(methods_personal_root()) / Path(path_str).name
        if cand.is_file():
            path = cand
        else:
            return
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return
    out = []
    replaced = False
    for i, line in enumerate(lines):
        out.append(line)
        if i == 0:
            continue
        if line.strip() == "---":
            break
        if line.startswith("strength:"):
            out[-1] = f"strength: {strength}\n"
            replaced = True
    if replaced:
        path.write_text("".join(out), encoding="utf-8")


def cmd_technique(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: kb technique bump <id|path|filename> [--to used|repeated|contradicted|hypothesis]")
        print("       kb technique hit <id|path|filename>   # +1 hit_count")
        return 2
    sub = argv[0]
    rest = argv[1:]
    if sub == "bump":
        if not rest:
            print("usage: kb technique bump <id|path|filename> [--to STRENGTH]")
            return 2
        needle = rest[0]
        to = None
        if "--to" in rest:
            to = rest[rest.index("--to") + 1]
        result = bump_strength(needle, to=to)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if sub == "hit":
        if not rest:
            print("usage: kb technique hit <id|path|filename>")
            return 2
        n = record_hits([rest[0]])
        append_event("technique_manual_hit", path=rest[0], updated=n)
        print(json.dumps({"updated": n, "path": rest[0]}, ensure_ascii=False))
        return 0
    print(f"unknown technique subcommand: {sub}")
    return 2
