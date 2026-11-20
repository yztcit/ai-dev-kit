#!/usr/bin/env python3
"""Deposit apply: validate all-or-nothing, then write facts / techniques / plan counts."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from events import append_event
from memory_paths import ensure_layout, facts_root, methods_personal_root, personal_techniques_index_path

COUNTEREXAMPLE_HEADING = "## 反例"
PLAN_KINDS = frozenset({"exec", "reference"})


def _load_index() -> dict:
    path = Path(personal_techniques_index_path())
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass
    return {"schema": 1, "entries": []}


def _save_index(data: dict) -> None:
    ensure_layout()
    path = Path(personal_techniques_index_path())
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def validate_deposit(payload) -> tuple[bool, list[str]]:
    """Return (ok, reasons). Reasons may include schema, missing_counterexample, missing_plan_kind."""
    reasons: list[str] = []
    if not isinstance(payload, dict):
        return False, ["schema"]

    for key in ("facts", "techniques", "plans"):
        if key not in payload:
            reasons.append("schema")
        elif not isinstance(payload[key], list):
            reasons.append("schema")

    if reasons:
        return False, _dedupe(reasons)

    for fact in payload["facts"]:
        if not isinstance(fact, dict):
            reasons.append("schema")
            continue
        if "path" in fact or "body" in fact:
            if not fact.get("path") or fact.get("body") is None:
                reasons.append("schema")

    for tech in payload["techniques"]:
        if not isinstance(tech, dict):
            reasons.append("schema")
            continue
        tid = tech.get("id")
        triggers = tech.get("triggers")
        body_md = tech.get("body_md")
        if not tid or not isinstance(triggers, list) or body_md is None:
            reasons.append("schema")
        elif COUNTEREXAMPLE_HEADING not in str(body_md):
            reasons.append("missing_counterexample")

    for plan in payload["plans"]:
        if not isinstance(plan, dict):
            reasons.append("schema")
            continue
        if plan.get("kind") not in PLAN_KINDS:
            reasons.append("missing_plan_kind")

    return (len(reasons) == 0, _dedupe(reasons))


def _dedupe(reasons: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def _technique_card(tech: dict) -> str:
    tid = str(tech["id"])
    triggers = tech.get("triggers") or []
    strength = str(tech.get("strength") or "hypothesis")
    scope = str(tech.get("scope") or "personal")
    verified = tech.get("verified_at") or datetime.now().astimezone().strftime("%Y-%m-%d")
    body_md = str(tech.get("body_md") or "").strip()
    if not body_md.endswith("\n"):
        body_md += "\n"
    triggers_json = json.dumps(triggers, ensure_ascii=False)
    header = (
        "---\n"
        f"id: {tid}\n"
        "kind: technique\n"
        f"triggers: {triggers_json}\n"
        f"scope: {scope}\n"
        f"verified_at: {verified}\n"
        f"strength: {strength}\n"
        "---\n\n"
    )
    return header + body_md


def _upsert_index_entry(entries: list[dict], path: str, tech: dict) -> None:
    tid = str(tech["id"])
    triggers = tech.get("triggers") or []
    strength = str(tech.get("strength") or "hypothesis")
    row = {"id": tid, "path": path, "triggers": triggers, "strength": strength}
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        if str(entry.get("id") or "") == tid or Path(str(entry.get("path") or "")).name == f"{tid}.md":
            entries[i] = row
            return
    entries.append(row)


def apply_deposit(payload) -> dict:
    ok, reasons = validate_deposit(payload)
    if not ok:
        append_event("deposit_rejected", reasons=reasons)
        return {"ok": False, "reasons": reasons}

    ensure_layout()
    written_paths: list[str] = []

    for fact in payload.get("facts") or []:
        rel = str(fact["path"]).lstrip("/")
        dest = Path(facts_root()) / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(str(fact["body"]), encoding="utf-8")
        written_paths.append(str(dest.resolve()))

    index = _load_index()
    entries = [e for e in index.get("entries", []) if isinstance(e, dict)]

    for tech in payload.get("techniques") or []:
        tid = str(tech["id"])
        card_path = Path(methods_personal_root()) / f"{tid}.md"
        card_path.write_text(_technique_card(tech), encoding="utf-8")
        resolved = str(card_path.resolve())
        written_paths.append(resolved)
        _upsert_index_entry(entries, resolved, tech)

    index["entries"] = entries
    _save_index(index)

    plans = payload.get("plans") or []
    plans_count = len(plans)

    fact_count = len(payload.get("facts") or [])
    technique_count = len(payload.get("techniques") or [])

    row = append_event(
        "deposit",
        fact_count=fact_count,
        technique_count=technique_count,
        plans_count=plans_count,
        paths=written_paths,
    )
    return {
        "ok": True,
        "fact_count": fact_count,
        "technique_count": technique_count,
        "plans_count": plans_count,
        "paths": written_paths,
        "event": row,
    }


def _read_payload_json(argv: list[str]) -> tuple[dict | None, int]:
    path = None
    i = 0
    while i < len(argv):
        if argv[i] == "--file" and i + 1 < len(argv):
            path = argv[i + 1]
            i += 2
            continue
        if argv[i] in ("-h", "--help"):
            print("usage: kb deposit-apply [--file PATH]")
            print("       (omit --file to read JSON from stdin)")
            return None, 0
        i += 1
    try:
        if path:
            raw = Path(path).read_text(encoding="utf-8")
        else:
            raw = sys.stdin.read()
        data = json.loads(raw)
        if not isinstance(data, dict):
            print("error: JSON root must be an object")
            return None, 2
        return data, 0
    except OSError as e:
        print(f"cannot read payload: {e}")
        return None, 2
    except ValueError as e:
        print(f"invalid JSON: {e}")
        return None, 2


def cmd_deposit_apply(argv):
    payload, code = _read_payload_json(argv)
    if code != 0 or payload is None:
        return code if code else 2
    result = apply_deposit(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(cmd_deposit_apply(sys.argv[1:]))