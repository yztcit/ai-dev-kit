#!/usr/bin/env python3
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]


class NoteOpsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        os.environ["DEV_MEMORY_ROOT"] = str(self.root)
        sys.path.insert(0, str(ENGINE))
        for name in ("memory_paths", "events", "note_ops"):
            sys.modules.pop(name, None)
        import memory_paths
        import events
        import note_ops

        self.memory = memory_paths
        self.events = events
        self.note_ops = note_ops
        self.memory.ensure_layout()

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("DEV_MEMORY_ROOT", None)

    def test_write_note_creates_scratch_file_and_event(self):
        result = self.note_ops.write_note(slug="t", body="hi")
        scratch = Path(self.memory.scratch_root())
        self.assertTrue(scratch.is_dir())
        path = Path(result["path"])
        self.assertTrue(path.is_file())
        self.assertEqual(path.read_text(encoding="utf-8"), "hi")
        self.assertRegex(path.name, r"^\d{8}-\d{6}-t\.md$")
        summary = self.events.summarize(days=30)
        self.assertGreaterEqual(summary["event_counts"].get("note", 0), 1)


if __name__ == "__main__":
    unittest.main()