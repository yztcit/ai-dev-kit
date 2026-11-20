#!/usr/bin/env python3
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]


class BrowseOpsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        os.environ["DEV_MEMORY_ROOT"] = str(self.root)
        sys.path.insert(0, str(ENGINE))
        for name in (
            "memory_paths",
            "events",
            "todo_ops",
            "habit_ops",
            "note_ops",
            "browse_ops",
        ):
            sys.modules.pop(name, None)
        import memory_paths
        import todo_ops
        import habit_ops
        import note_ops
        import browse_ops

        self.memory = memory_paths
        self.todo_ops = todo_ops
        self.habit_ops = habit_ops
        self.note_ops = note_ops
        self.browse = browse_ops
        self.memory.ensure_layout()

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("DEV_MEMORY_ROOT", None)

    def test_ls_scratch_technique_habit_todo_unified_keys(self):
        self.note_ops.write_note(slug="alpha", body="hello scratch")
        self.habit_ops.upsert_habit(habit_id="lang", title="语言", body="中文")
        self.todo_ops.add_todo(title="ship", due="2030-01-01")
        idx = {
            "entries": [
                {
                    "id": "t1",
                    "path": "t1.md",
                    "strength": "used",
                    "hit_count": 2,
                    "triggers": ["排查"],
                }
            ]
        }
        Path(self.memory.personal_techniques_index_path()).write_text(
            json.dumps(idx), encoding="utf-8"
        )
        (Path(self.memory.methods_personal_root()) / "t1.md").write_text(
            "# t1\nbody\n", encoding="utf-8"
        )

        for kind in ("scratch", "technique", "habit", "todo"):
            rows = self.browse.list_type(kind, limit=None)
            self.assertTrue(rows, msg=kind)
            row = rows[0]
            for key in ("type", "id", "title_or_slug", "meta", "path"):
                self.assertIn(key, row)
            self.assertEqual(row["type"], kind)

    def test_show_habit_and_todo(self):
        self.habit_ops.upsert_habit(habit_id="lang", title="语言", body="简体中文")
        text = self.browse.show_item("habit", "lang")
        self.assertIn("简体中文", text)
        todo = self.todo_ops.add_todo(title="one")
        shown = self.browse.show_item("todo", todo["id"])
        self.assertIn("one", shown)

    def test_facts_all_lists_files(self):
        entry = Path(self.memory.facts_root()) / "host" / "g" / "repo"
        (entry / "base").mkdir(parents=True)
        (entry / "base" / "CLAUDE.md").write_text("# hi\n", encoding="utf-8")
        rows = self.browse.list_facts(all_repos=True)
        self.assertTrue(any(r["id"].endswith("base/CLAUDE.md") for r in rows))


if __name__ == "__main__":
    unittest.main()
