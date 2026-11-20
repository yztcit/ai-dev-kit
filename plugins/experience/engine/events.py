#!/usr/bin/env python3
"""Append-only ops log for personal experience feedback."""
from __future__ import annotations

import hashlib
import json
import os
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from memory_paths import ensure_layout, events_path, personal_techniques_index_path


def _now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def prompt_fingerprint(text: str) -> dict:
    raw = (text or "").strip()
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16] if raw else ""
    preview = raw.replace("\n", " ")
    if len(preview) > 80:
        preview = preview[:77] + "..."
    return {"prompt_sha": digest, "prompt_preview": preview}


def append_event(event_type: str, **fields) -> dict:
    ensure_layout()
    payload = {"ts": _now_iso(), "type": event_type}
    payload.update({k: v for k, v in fields.items() if v is not None})
    path = Path(events_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return payload


def iter_events(limit: int | None = None):
    path = Path(events_path())
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    rows = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    if limit is not None and limit > 0:
        return rows[-limit:]
    return rows


def _bump_candidates() -> list[dict]:
    path = Path(personal_techniques_index_path())
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    entries = data.get("entries") if isinstance(data, dict) else []
    out = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        strength = str(entry.get("strength") or "hypothesis").strip().lower()
        hits = int(entry.get("hit_count") or 0)
        if strength == "hypothesis" and hits >= 3:
            out.append(
                {
                    "id": entry.get("id"),
                    "path": entry.get("path"),
                    "hit_count": hits,
                    "strength": strength,
                }
            )
    return out


def summarize(days: int = 30, limit: int = 5000) -> dict:
    cutoff = time.time() - max(days, 1) * 86400
    counts = Counter()
    hit_paths = Counter()
    recent = []
    for row in iter_events(limit=limit):
        ts = row.get("ts") or ""
        try:
            # fromisoformat handles offsets
            epoch = datetime.fromisoformat(ts).timestamp()
        except ValueError:
            epoch = 0
        if epoch and epoch < cutoff:
            continue
        et = str(row.get("type") or "unknown")
        counts[et] += 1
        if et == "technique_hit":
            for p in row.get("paths") or []:
                hit_paths[str(p)] += 1
        recent.append(row)
    bump = _bump_candidates()
    return {
        "days": days,
        "event_counts": dict(counts),
        "top_hits": hit_paths.most_common(10),
        "bump_candidates": bump,
        "recent": recent[-20:],
        "events_file": events_path(),
    }


def cmd_event(argv):
    """kb event <type> [--key value ...] [--json-field key=json]"""
    if not argv:
        print("usage: kb event <type> [--path P] [--slug S] [--repo R] [--checkout C] ...")
        return 2
    event_type = argv[0]
    fields = {}
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg.startswith("--") and i + 1 < len(argv):
            key = arg[2:].replace("-", "_")
            val = argv[i + 1]
            if key == "json":
                try:
                    fields.update(json.loads(val))
                except ValueError:
                    print(f"invalid --json: {val}")
                    return 2
            else:
                fields[key] = val
            i += 2
            continue
        i += 1
    row = append_event(event_type, **fields)
    print(json.dumps(row, ensure_ascii=False))
    return 0


def cmd_report(argv):
    days = 30
    as_json = False
    i = 0
    while i < len(argv):
        if argv[i] == "--days" and i + 1 < len(argv):
            days = int(argv[i + 1])
            i += 2
            continue
        if argv[i] == "--json":
            as_json = True
            i += 1
            continue
        i += 1
    summary = summarize(days=days)
    if as_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    print(f"experience report · last {days}d · {summary['events_file']}")
    if not summary["event_counts"]:
        print("  (no events yet — use Claude normally; hits/notes/deposits will appear here)")
        return 0
    print("  counts:")
    for k, v in sorted(summary["event_counts"].items()):
        print(f"    {k}: {v}")
    if summary["top_hits"]:
        print("  top technique hits:")
        for path, n in summary["top_hits"]:
            print(f"    {n}× {path}")
    if summary.get("bump_candidates"):
        print("  bump candidates (hit≥3, hypothesis):")
        for item in summary["bump_candidates"]:
            label = item.get("id") or item.get("path") or "?"
            print(f"    {label} · {item.get('hit_count')} hits · kb technique bump {label}")
    return 0


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "report":
        raise SystemExit(cmd_report(sys.argv[2:]))
    raise SystemExit(cmd_event(sys.argv[1:]))
