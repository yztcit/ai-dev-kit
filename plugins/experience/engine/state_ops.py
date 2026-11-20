#!/usr/bin/env python3
"""Read/write personal experience on/off state."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

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


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def set_enabled(enabled: bool) -> None:
    ensure_layout()
    data = _load_state()
    data["schema"] = 1
    data["enabled"] = bool(enabled)
    if enabled:
        data.pop("disabled_at", None)
    else:
        data["disabled_at"] = _now_iso()
    path = state_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
        f.write("\n")


def cmd_off(argv) -> int:
    set_enabled(False)
    print("experience kb · OFF（hooks 将跳过注入；`kb on` 恢复）")
    return 0


def cmd_on(argv) -> int:
    set_enabled(True)
    print("experience kb · ON")
    return 0