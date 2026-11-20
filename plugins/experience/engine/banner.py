#!/usr/bin/env python3
"""One-line SessionStart banner for experience kb."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from state_ops import is_enabled

_OFF = "[experience] kb OFF · 输入 /kb-on 或 kb on 恢复"
_MAX_LEN = 200


def _kb_module():
    engine = Path(__file__).resolve().parent
    name = "experience_kb_for_banner"
    if name in sys.modules:
        return sys.modules[name]
    if str(engine) not in sys.path:
        sys.path.insert(0, str(engine))
    from importlib.machinery import SourceFileLoader
    import importlib.util

    loader = SourceFileLoader(name, str(engine / "kb"))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    sys.modules[name] = mod
    return mod


def format_banner(checkout: str | None = None) -> str:
    if not is_enabled():
        return _OFF

    checkout = os.path.realpath(
        checkout or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    )

    habits_n = 0
    overdue_n = 0
    try:
        from habit_ops import list_habits
        from todo_ops import list_todos

        habits_n = len(list_habits())
        overdue_n = len(list_todos(overdue_only=True))
    except Exception:
        pass

    key = ""
    branch = ""
    try:
        kb = _kb_module()
        key = (kb.repo_identity(checkout) or "").strip()
        branch = (kb.current_branch(checkout) or "").strip()
    except Exception:
        pass

    parts = ["[experience] kb ON"]
    if key:
        parts.append(f"{key}@{branch}" if branch else key)
    parts.append(f"习惯{habits_n}")
    parts.append(f"逾期{overdue_n}")

    line = " · ".join(parts)
    if len(line) > _MAX_LEN:
        line = line[: _MAX_LEN - 1] + "…"
    return line