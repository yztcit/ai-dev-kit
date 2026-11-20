#!/usr/bin/env python3
import json
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
ENGINE = Path(__file__).resolve().parents[1]


class TodoHabitOpsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        os.environ["DEV_MEMORY_ROOT"] = str(self.root)
        sys.path.insert(0, str(ENGINE))
        for name in ("memory_paths", "events", "todo_ops", "habit_ops"):
            sys.modules.pop(name, None)
        import memory_paths
        import events
        import todo_ops
        import habit_ops

        self.memory = memory_paths
        self.events = events
        self.todo_ops = todo_ops
        self.habit_ops = habit_ops
        self.memory.ensure_layout()

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("DEV_MEMORY_ROOT", None)

    def _items_path(self):
        return Path(self.memory.todos_root()) / "items.jsonl"

    def test_todo_add_appends_jsonl_and_todo_add_event(self):
        row = self.todo_ops.add_todo(title="ship feature", due="2030-01-15")
        self.assertEqual(row["title"], "ship feature")
        self.assertEqual(row["due"], "2030-01-15")
        self.assertEqual(row["status"], "open")
        self.assertTrue(row.get("id"))
        self.assertTrue(row.get("created_at"))
        lines = self._items_path().read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)
        stored = json.loads(lines[0])
        self.assertEqual(stored["id"], row["id"])
        types = [r.get("type") for r in self.events.iter_events()]
        self.assertIn("todo_add", types)

    def test_todo_done_marks_done_and_emits_event(self):
        row = self.todo_ops.add_todo(title="close loop")
        updated = self.todo_ops.mark_done(row["id"])
        self.assertEqual(updated["status"], "done")
        stored = json.loads(self._items_path().read_text(encoding="utf-8").strip())
        self.assertEqual(stored["status"], "done")
        done_rows = [r for r in self.events.iter_events() if r.get("type") == "todo_done"]
        self.assertEqual(len(done_rows), 1)
        self.assertEqual(done_rows[0].get("id"), row["id"])

    def test_todo_list_overdue_filters_open_past_due(self):
        past = (date.today() - timedelta(days=2)).isoformat()
        future = (date.today() + timedelta(days=2)).isoformat()
        self.todo_ops.add_todo(title="late", due=past)
        self.todo_ops.add_todo(title="ok", due=future)
        done_row = self.todo_ops.add_todo(title="late-done", due=past)
        self.todo_ops.mark_done(done_row["id"])
        overdue = self.todo_ops.list_todos(overdue_only=True)
        titles = {t["title"] for t in overdue}
        self.assertEqual(titles, {"late"})

    def test_habit_upsert_writes_card_index_and_event(self):
        result = self.habit_ops.upsert_habit(
            habit_id="commit-msg-style", title="提交信息", body="一行说明动机"
        )
        card = Path(self.memory.habits_root()) / "commit-msg-style.md"
        self.assertTrue(card.is_file())
        text = card.read_text(encoding="utf-8")
        self.assertIn("id: commit-msg-style", text)
        self.assertIn("title: 提交信息", text)
        self.assertIn("一行说明动机", text)
        idx = json.loads(Path(self.memory.habits_index_path()).read_text(encoding="utf-8"))
        self.assertEqual(idx["schema"], 1)
        ids = {e["id"] for e in idx["entries"]}
        self.assertIn("commit-msg-style", ids)
        self.assertEqual(result["path"], str(card.resolve()))
        types = [r.get("type") for r in self.events.iter_events()]
        self.assertIn("habit_upsert", types)

    def test_habit_upsert_updates_existing_card_and_index(self):
        self.habit_ops.upsert_habit(habit_id="lang", title="语言", body="中文")
        self.habit_ops.upsert_habit(habit_id="lang", title="语言偏好", body="简体")
        card = Path(self.memory.habits_root()) / "lang.md"
        self.assertIn("title: 语言偏好", card.read_text(encoding="utf-8"))
        idx = json.loads(Path(self.memory.habits_index_path()).read_text(encoding="utf-8"))
        self.assertEqual(len(idx["entries"]), 1)
        self.assertEqual(idx["entries"][0]["title"], "语言偏好")

    def test_habit_list_returns_index_entries(self):
        self.habit_ops.upsert_habit(habit_id="a", title="A", body="x")
        self.habit_ops.upsert_habit(habit_id="b", title="B", body="y")
        items = self.habit_ops.list_habits()
        self.assertEqual(len(items), 2)
        self.assertEqual({h["id"] for h in items}, {"a", "b"})


if __name__ == "__main__":
    unittest.main()