#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path


DEFAULT_INDEX_PATH = Path(__file__).resolve().parents[1] / "techniques" / "index.json"
STRENGTH_RANK = {
    "repeated": 0,
    "used": 1,
    "hypothesis": 2,
    "contradicted": 99,
}


def load_index(index_path=None):
    path = Path(index_path or os.environ.get("EXPERIENCE_TECHNIQUES_INDEX") or DEFAULT_INDEX_PATH)
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except (OSError, ValueError):
        pass
    return {"schema": 1, "entries": []}


def normalize_entries(triggers):
    if isinstance(triggers, dict):
        entries = triggers.get("entries", [])
    else:
        entries = triggers or []
    return [entry for entry in entries if isinstance(entry, dict)]


def _strength_allowed(strength, allowed_strengths):
    strength = (strength or "hypothesis").strip().lower()
    if strength == "contradicted":
        return False
    if not allowed_strengths:
        return True
    allowed = {item.strip().lower() for item in allowed_strengths if item}
    return strength in allowed


def _entry_matches(entry, text):
    text = (text or "").strip()
    if not text:
        return True
    haystack = text.lower()
    for trigger in entry.get("triggers") or []:
        needle = str(trigger).strip().lower()
        if needle and needle in haystack:
            return True
    return False


def match(triggers, text, allowed_strengths=None, limit=None):
    matched = []
    for entry in normalize_entries(triggers):
        strength = (entry.get("strength") or "hypothesis").strip().lower()
        if not _strength_allowed(strength, allowed_strengths):
            continue
        if not _entry_matches(entry, text):
            continue
        path = str(entry.get("path") or "").strip()
        if not path:
            continue
        matched.append((STRENGTH_RANK.get(strength, 50), path))
    matched.sort(key=lambda item: (item[0], item[1]))
    paths = [path for _rank, path in matched]
    if limit is not None:
        return paths[:limit]
    return paths


def match_index(text, index_path=None, allowed_strengths=None, limit=None):
    return match(load_index(index_path=index_path), text, allowed_strengths=allowed_strengths, limit=limit)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Match startup techniques by trigger and strength.")
    parser.add_argument("--text", default="", help="User text or startup text")
    parser.add_argument("--index", default="", help="Technique index path")
    parser.add_argument("--strengths", default="", help="Comma-separated strength allowlist")
    parser.add_argument("--limit", type=int, default=0, help="Max results, 0 means unlimited")
    parser.add_argument("--json", action="store_true", help="Print as JSON array")
    args = parser.parse_args(argv)

    strengths = [item for item in args.strengths.split(",") if item.strip()] or None
    limit = args.limit if args.limit > 0 else None
    results = match_index(
        args.text,
        index_path=args.index or None,
        allowed_strengths=strengths,
        limit=limit,
    )
    if args.json:
        print(json.dumps(results, ensure_ascii=False))
    else:
        for item in results:
            print(item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
