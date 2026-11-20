#!/usr/bin/env python3
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]


class DoctorOffHelpReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        os.environ["DEV_MEMORY_ROOT"] = str(self.root)
        sys.path.insert(0, str(ENGINE))
        for name in (
            "memory_paths",
            "state_ops",
            "help_ops",
            "events",
            "doctor",
            "habit_ops",
            "todo_ops",
        ):
            sys.modules.pop(name, None)
        import memory_paths
        import state_ops
        import help_ops
        import events
        import doctor

        self.memory = memory_paths
        self.state_ops = state_ops
        self.help_ops = help_ops
        self.events = events
        self.doctor = doctor
        self.memory.ensure_layout()

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("DEV_MEMORY_ROOT", None)

    def test_off_sets_is_enabled_false(self):
        self.assertTrue(self.state_ops.is_enabled())
        self.state_ops.cmd_off([])
        self.assertFalse(self.state_ops.is_enabled())
        state = json.loads(Path(self.memory.state_path()).read_text(encoding="utf-8"))
        self.assertIn("disabled_at", state)

    def test_help_returns_zero(self):
        self.assertEqual(self.help_ops.cmd_help([]), 0)
        self.assertEqual(self.help_ops.cmd_help(["todo"]), 0)

    def test_report_includes_new_keys(self):
        self.events.append_event("todo_add", id="t1", title="a")
        self.events.append_event("todo_done", id="t1", title="a")
        self.events.append_event("habit_upsert", id="h1", title="H")
        self.events.append_event("deposit_rejected", reasons=["bad"])
        idx = Path(self.memory.personal_techniques_index_path())
        idx.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "entries": [
                        {
                            "id": "bump-me",
                            "path": "bump-me.md",
                            "strength": "hypothesis",
                            "hit_count": 3,
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        summary = self.events.summarize(days=30)
        self.assertEqual(summary["event_counts"].get("deposit_rejected"), 1)
        self.assertEqual(summary["event_counts"].get("todo_add"), 1)
        self.assertEqual(summary["event_counts"].get("todo_done"), 1)
        self.assertEqual(summary["event_counts"].get("habit_upsert"), 1)
        self.assertIn("bump_candidates", summary)
        self.assertEqual(len(summary["bump_candidates"]), 1)
        self.assertEqual(summary["bump_candidates"][0]["id"], "bump-me")

    def test_doctor_disabled_ok_true(self):
        self.state_ops.set_enabled(False)
        plugin = ENGINE.parent
        result = self.doctor.run_doctor(plugin)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "DISABLED")
        kb = next(c for c in result["checks"] if c["name"] == "kb_enabled")
        self.assertEqual(kb["detail"], "DISABLED")
        self.assertTrue(kb["ok"])


if __name__ == "__main__":
    unittest.main()