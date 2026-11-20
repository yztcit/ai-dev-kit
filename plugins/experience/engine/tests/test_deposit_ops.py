#!/usr/bin/env python3
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]


class DepositOpsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        os.environ["DEV_MEMORY_ROOT"] = str(self.root)
        sys.path.insert(0, str(ENGINE))
        for name in ("memory_paths", "events", "deposit_ops"):
            sys.modules.pop(name, None)
        import memory_paths
        import events
        import deposit_ops

        self.memory = memory_paths
        self.events = events
        self.deposit_ops = deposit_ops
        self.memory.ensure_layout()

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("DEV_MEMORY_ROOT", None)

    def test_reject_missing_counterexample(self):
        payload = {
            "facts": [],
            "techniques": [
                {"id": "x", "triggers": ["a"], "body_md": "## 情境\n## 做法\n"},
            ],
            "plans": [],
        }
        ok, reasons = self.deposit_ops.validate_deposit(payload)
        self.assertFalse(ok)
        self.assertIn("missing_counterexample", reasons)
        r = self.deposit_ops.apply_deposit(payload)
        self.assertFalse(r["ok"])
        personal = Path(self.memory.methods_personal_root())
        self.assertFalse(list(personal.glob("x.md")))
        summary = self.events.summarize(days=30)
        self.assertGreaterEqual(summary["event_counts"].get("deposit_rejected", 0), 1)

    def test_success_writes_technique_with_counterexample_and_deposit_event(self):
        payload = {
            "facts": [],
            "techniques": [
                {
                    "id": "ok-tech",
                    "triggers": ["动手前"],
                    "body_md": "## 情境\n语境\n## 做法\n步骤\n## 反例\n不适合时\n",
                },
            ],
            "plans": [],
        }
        r = self.deposit_ops.apply_deposit(payload)
        self.assertTrue(r["ok"])
        card = Path(self.memory.methods_personal_root()) / "ok-tech.md"
        self.assertTrue(card.is_file())
        text = card.read_text(encoding="utf-8")
        self.assertIn("## 反例", text)
        self.assertIn('id: ok-tech', text)
        index = json.loads(
            Path(self.memory.personal_techniques_index_path()).read_text(encoding="utf-8")
        )
        paths = {e.get("path") for e in index.get("entries", [])}
        self.assertTrue(any("ok-tech.md" in (p or "") for p in paths))
        rows = self.events.iter_events()
        deposit_rows = [row for row in rows if row.get("type") == "deposit"]
        self.assertEqual(len(deposit_rows), 1)
        self.assertEqual(deposit_rows[0].get("technique_count"), 1)
        self.assertEqual(deposit_rows[0].get("fact_count"), 0)
        self.assertEqual(deposit_rows[0].get("plans_count"), 0)


if __name__ == "__main__":
    unittest.main()