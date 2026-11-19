#!/usr/bin/env python3
import json
from pathlib import Path

from memory_paths import methods_personal_root


SEED_DIR_NAME = "seed_techniques"


def _seed_dir(plugin_dir):
    return Path(plugin_dir) / SEED_DIR_NAME


def _personal_dir():
    return Path(methods_personal_root())


def _personal_index_path():
    return _personal_dir() / "index.json"


def _load_index(path):
    try:
        with Path(path).open(encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except (OSError, ValueError):
        pass
    return {"schema": 1, "entries": []}


def _save_index(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    tmp.replace(path)


def _read_frontmatter(path):
    text = Path(path).read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    meta = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key == "triggers":
            try:
                meta[key] = json.loads(value)
            except ValueError:
                meta[key] = []
        else:
            meta[key] = value
    return meta


def ensure_seed_techniques(plugin_dir):
    personal_dir = _personal_dir()
    personal_dir.mkdir(parents=True, exist_ok=True)
    index_path = _personal_index_path()
    doc = _load_index(index_path)
    entries = [entry for entry in doc.get("entries", []) if isinstance(entry, dict)]
    existing_paths = {str(entry.get("path") or "").strip() for entry in entries}
    copied = 0

    for seed in sorted(_seed_dir(plugin_dir).glob("*.md")):
        destination = personal_dir / seed.name
        if not destination.exists():
            destination.write_text(seed.read_text(encoding="utf-8"), encoding="utf-8")
            copied += 1
        dest_path = str(destination)
        if dest_path in existing_paths:
            continue
        meta = _read_frontmatter(seed)
        entries.append(
            {
                "path": dest_path,
                "triggers": meta.get("triggers") or [],
                "strength": meta.get("strength") or "hypothesis",
            }
        )
        existing_paths.add(dest_path)

    doc["schema"] = doc.get("schema", 1) or 1
    doc["entries"] = entries
    _save_index(index_path, doc)
    return copied
