#!/usr/bin/env python3
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]


class EventsAndDoctorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        os.environ["DEV_MEMORY_ROOT"] = str(self.root)
        sys.path.insert(0, str(ENGINE))
        for name in (
            "memory_paths",
            "events",
            "technique_ops",
            "doctor",
            "bootstrap_seeds",
        ):
            sys.modules.pop(name, None)
        import memory_paths
        import events
        import technique_ops

        self.memory = memory_paths
        self.events = events
        self.technique_ops = technique_ops
        self.memory.ensure_layout()

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("DEV_MEMORY_ROOT", None)

    def test_append_and_report(self):
        row = self.events.append_event("technique_hit", paths=["a.md"], strengths=["used"])
        self.assertEqual(row["type"], "technique_hit")
        self.assertTrue(Path(self.events.events_path()).is_file())
        summary = self.events.summarize(days=30)
        self.assertEqual(summary["event_counts"].get("technique_hit"), 1)

    def test_technique_bump_and_hit_count(self):
        idx = Path(self.memory.personal_techniques_index_path())
        idx.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "entries": [
                        {
                            "id": "demo",
                            "path": "demo.md",
                            "triggers": ["demo"],
                            "strength": "hypothesis",
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        card = Path(self.memory.methods_personal_root()) / "demo.md"
        card.write_text("---\nid: demo\nstrength: hypothesis\n---\nbody\n", encoding="utf-8")
        self.technique_ops.record_hits(["demo.md"])
        data = json.loads(idx.read_text(encoding="utf-8"))
        self.assertEqual(data["entries"][0]["hit_count"], 1)
        result = self.technique_ops.bump_strength("demo")
        self.assertEqual(result["to"], "used")
        data = json.loads(idx.read_text(encoding="utf-8"))
        self.assertEqual(data["entries"][0]["strength"], "used")
        text = card.read_text(encoding="utf-8")
        self.assertIn("strength: used", text)


if __name__ == "__main__":
    unittest.main()
