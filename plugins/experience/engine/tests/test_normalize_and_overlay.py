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
    try:
        name = f"kb_test_{uuid.uuid4().hex}"
        loader = SourceFileLoader(name, str(KB_PATH))
        spec = importlib.util.spec_from_loader(name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(ENGINE_DIR))
        os.environ.pop("DEV_MEMORY_ROOT", None)


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


class KbPortTests(unittest.TestCase):
    def test_normalize_https_and_ssh_same(self):
        with tempfile.TemporaryDirectory() as td:
            kb = load_kb(Path(td))
            a = kb.normalize_remote("https://git.example.com/group/repo.git")
            b = kb.normalize_remote("git@git.example.com:group/repo.git")
            self.assertEqual(a, "git.example.com/group/repo")
            self.assertEqual(a, b)

    def test_detect_overlay_personal_when_kb_paths_untracked(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()
            git(repo, "init")
            git(repo, "config", "user.name", "Test User")
            git(repo, "config", "user.email", "test@example.com")
            git(repo, "remote", "add", "origin", "git@git.example.com:group/repo.git")
            git(repo, "commit", "--allow-empty", "-m", "init")

            kb = load_kb(Path(td) / "memory")
            self.assertEqual(kb.detect_overlay(str(repo)), "personal")

    def test_detect_overlay_team_tracked_when_team_files_tracked(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()
            git(repo, "init")
            git(repo, "config", "user.name", "Test User")
            git(repo, "config", "user.email", "test@example.com")
            git(repo, "remote", "add", "origin", "git@git.example.com:group/repo.git")
            write(repo / "CLAUDE.md", "team claude\n")
            git(repo, "add", "CLAUDE.md")
            git(repo, "commit", "-m", "init")

            kb = load_kb(Path(td) / "memory")
            self.assertEqual(kb.detect_overlay(str(repo)), "team-tracked")

    def test_sync_team_tracked_routes_root_docs_and_skips_tracked_paths(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            memory_root = td_path / "memory"
            repo = td_path / "repo"
            repo.mkdir()
            git(repo, "init")
            git(repo, "config", "user.name", "Test User")
            git(repo, "config", "user.email", "test@example.com")
            git(repo, "remote", "add", "origin", "git@git.example.com:group/repo.git")
            write(repo / "CLAUDE.md", "team claude\n")
            write(repo / ".claude" / "settings.json", '{"team": true}\n')
            git(repo, "add", "CLAUDE.md", ".claude/settings.json")
            git(repo, "commit", "-m", "init")

            entry = memory_root / "facts" / "git.example.com" / "group" / "repo"
            write(entry / "base" / "CLAUDE.md", "personal claude\n")
            write(entry / "base" / "AGENTS.md", "personal agents\n")
            write(entry / "base" / "settings.json", '{"personal": true}\n')
            write(entry / "base" / "rules" / "rule.md", "rule\n")
            write(entry / "kb.yml", "schema: 1\nname: repo\noverlay: personal\n")
            write(
                memory_root / "index.json",
                json.dumps(
                    {
                        "schema": 1,
                        "entries": {
                            "git.example.com/group/repo": "facts/git.example.com/group/repo"
                        },
                        "never_remind": [],
                    }
                )
                + "\n",
            )

            kb = load_kb(memory_root)
            code, lines = kb.sync(str(repo))

            self.assertEqual(code, 0)
            self.assertEqual((repo / "CLAUDE.md").read_text(encoding="utf-8"), "team claude\n")
            self.assertEqual(
                (repo / ".claude" / "personal" / "CLAUDE.md").read_text(encoding="utf-8"),
                "personal claude\n",
            )
            self.assertEqual(
                (repo / ".claude" / "personal" / "AGENTS.md").read_text(encoding="utf-8"),
                "personal agents\n",
            )
            self.assertEqual(
                (repo / ".claude" / "settings.json").read_text(encoding="utf-8"),
                '{"team": true}\n',
            )
            self.assertEqual(
                (repo / ".claude" / "rules" / "rule.md").read_text(encoding="utf-8"),
                "rule\n",
            )
            self.assertTrue(any("跳过" in line and "settings.json" in line for line in lines))
            self.assertIn("overlay: team-tracked", (entry / "kb.yml").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
