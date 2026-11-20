#!/usr/bin/env python3
"""Read/write personal experience on/off state."""
from __future__ import annotations

import json
import os

from memory_paths import ensure_layout, state_path

_DEFAULT_STATE = {"schema": 1, "enabled": True}


def _load_state() -> dict:
    path = state_path()
    if not os.path.isfile(path):
        return dict(_DEFAULT_STATE)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return dict(_DEFAULT_STATE)
    return data


def is_enabled() -> bool:
    return bool(_load_state().get("enabled", True))


def set_enabled(enabled: bool) -> None:
    ensure_layout()
    data = _load_state()
    data["schema"] = 1
    data["enabled"] = bool(enabled)
    path = state_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
        f.write("\n")