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
PLUGIN_DIR = ENGINE_DIR.parent
HIT_TECHNIQUES_PATH = ENGINE_DIR / "hit_techniques.py"
SESSION_START_PATH = PLUGIN_DIR / "hooks" / "session_start.sh"


def load_python_file(path, extra_sys_path=None):
    if extra_sys_path:
        sys.path.insert(0, str(extra_sys_path))
    try:
        name = f"experience_test_{uuid.uuid4().hex}"
        loader = SourceFileLoader(name, str(path))
        spec = importlib.util.spec_from_loader(name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        return module
    finally:
        if extra_sys_path:
            sys.path.remove(str(extra_sys_path))


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


class HitTechniquesTests(unittest.TestCase):
    def test_match_is_case_insensitive_and_skips_contradicted(self):
        module = load_python_file(HIT_TECHNIQUES_PATH, extra_sys_path=ENGINE_DIR)

        matched = module.match(
            [
                {"path": "used.md", "triggers": ["Refactor"], "strength": "used"},
                {"path": "hypothesis.md", "triggers": ["refactor"], "strength": "hypothesis"},
                {"path": "blocked.md", "triggers": ["refactor"], "strength": "contradicted"},
            ],
            "Need REFACTOR advice",
        )

        self.assertEqual(matched, ["used.md", "hypothesis.md"])


class SessionStartTests(unittest.TestCase):
    def make_repo(self, root):
        repo = Path(root) / "repo"
        repo.mkdir()
        git(repo, "init")
        git(repo, "config", "user.name", "Test User")
        git(repo, "config", "user.email", "test@example.com")
        git(repo, "remote", "add", "origin", "git@git.example.com:group/repo.git")
        return repo

    def run_session_start(self, repo, memory_root, techniques_index=None):
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(repo)
        env["DEV_MEMORY_ROOT"] = str(memory_root)
        if techniques_index:
            env["EXPERIENCE_TECHNIQUES_INDEX"] = str(techniques_index)
        return subprocess.run(
            ["bash", str(SESSION_START_PATH)],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    def test_registered_team_tracked_repo_prints_personal_fact_and_techniques(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            memory_root = td_path / "memory"
            repo = self.make_repo(td_path)
            write(repo / "CLAUDE.md", "team claude\n")
            git(repo, "add", "CLAUDE.md")
            git(repo, "commit", "-m", "init")

            entry = memory_root / "facts" / "git.example.com" / "group" / "repo"
            write(entry / "base" / "PERSONAL.md", "# personal\n")
            write(entry / "kb.yml", "schema: 1\nname: repo\noverlay: team-tracked\n")
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
            techniques_index = td_path / "techniques.json"
            write(
                techniques_index,
                json.dumps(
                    {
                        "schema": 1,
                        "entries": [
                            {"path": "t1.md", "triggers": ["unused"], "strength": "used"},
                            {"path": "t2.md", "triggers": ["unused"], "strength": "repeated"},
                        ],
                    }
                )
                + "\n",
            )

            result = self.run_session_start(repo, memory_root, techniques_index=techniques_index)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("[personal-fact]", result.stdout)
            self.assertIn("PERSONAL.md", result.stdout)
            self.assertIn("[technique]", result.stdout)
            self.assertNotIn("未接入", result.stdout)

    def test_unregistered_repo_prints_onboarding_choices(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            repo = self.make_repo(td_path)

            result = self.run_session_start(repo, td_path / "memory")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("未接入", result.stdout)
            self.assertIn("import", result.stdout)
            self.assertIn("跳过", result.stdout)
            self.assertIn("永不提醒", result.stdout)


if __name__ == "__main__":
    unittest.main()
