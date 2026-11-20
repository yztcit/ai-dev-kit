#!/usr/bin/env python3
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from importlib.machinery import SourceFileLoader
from pathlib import Path


ENGINE_DIR = Path(__file__).resolve().parents[1]
KB_PATH = ENGINE_DIR / "kb"


def load_kb(memory_root):
    os.environ["DEV_MEMORY_ROOT"] = str(memory_root)
    sys.path.insert(0, str(ENGINE_DIR))
    sys.modules.pop("memory_paths", None)
    sys.modules.pop("events", None)
    try:
        name = f"kb_test_{uuid.uuid4().hex}"
        loader = SourceFileLoader(name, str(KB_PATH))
        spec = importlib.util.spec_from_loader(name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(ENGINE_DIR))


def git(repo, *args, check=True):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=check,
        capture_output=True,
        text=True,
    )


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class ImportBranchOverlayTests(unittest.TestCase):
    def test_feature_branch_writes_overlay_and_leaves_base_untouched(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            memory_root = td_path / "memory"
            repo = td_path / "repo"
            repo.mkdir()

            git(repo, "init")
            git(repo, "config", "user.name", "Test User")
            git(repo, "config", "user.email", "test@example.com")
            git(repo, "remote", "add", "origin", "git@git.example.com:group/repo.git")
            git(repo, "checkout", "-b", "main")
            git(repo, "checkout", "-b", "feature")

            write(repo / ".claude" / "rules" / "a.md", "feature rule\n")
            write(repo / ".claude" / "rules" / "same.md", "same\n")

            entry = memory_root / "facts" / "git.example.com" / "group" / "repo"
            write(entry / "base" / "rules" / "a.md", "base rule\n")
            write(entry / "base" / "rules" / "same.md", "same\n")

            kb = load_kb(memory_root)
            code = kb.cmd_import([str(repo)])

            self.assertEqual(code, 0)
            self.assertEqual((entry / "base" / "rules" / "a.md").read_text(encoding="utf-8"), "base rule\n")
            self.assertEqual(
                (entry / "branches" / "feature" / "rules" / "a.md").read_text(encoding="utf-8"),
                "feature rule\n",
            )
            self.assertFalse((entry / "branches" / "feature" / "rules" / "same.md").exists())

            rows = (memory_root / "logs" / "events.jsonl").read_text(encoding="utf-8").splitlines()
            event = json.loads(rows[-1])
            self.assertEqual(event["type"], "import")
            self.assertEqual(event["branch"], "feature")
            self.assertEqual(event["copied"], 1)

    def test_main_branch_imports_plans_tree(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            memory_root = td_path / "memory"
            repo = td_path / "repo"
            repo.mkdir()

            git(repo, "init")
            git(repo, "config", "user.name", "Test User")
            git(repo, "config", "user.email", "test@example.com")
            git(repo, "remote", "add", "origin", "git@git.example.com:group/repo.git")
            git(repo, "checkout", "-b", "main")

            write(repo / ".claude" / "plans" / "plan.md", "plan\n")

            kb = load_kb(memory_root)
            code = kb.cmd_import([str(repo)])

            entry = memory_root / "facts" / "git.example.com" / "group" / "repo"
            self.assertEqual(code, 0)
            self.assertEqual((entry / "base" / "plans" / "plan.md").read_text(encoding="utf-8"), "plan\n")

            rows = (memory_root / "logs" / "events.jsonl").read_text(encoding="utf-8").splitlines()
            event = json.loads(rows[-1])
            self.assertEqual(event["type"], "import")
            self.assertEqual(event["branch"], "main")
            self.assertEqual(event["copied"], 1)


if __name__ == "__main__":
    unittest.main()
