#!/usr/bin/env python3
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
PLUGIN = ENGINE.parent


class PromoteOpsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plugin = self.root / "plugin"
        self.plugin.mkdir()
        os.environ["DEV_MEMORY_ROOT"] = str(self.root / "mem")
        os.environ["EXPERIENCE_PLUGIN_ROOT"] = str(self.plugin)
        sys.path.insert(0, str(ENGINE))
        for name in ("memory_paths", "events", "technique_ops", "promote_ops", "doctor"):
            sys.modules.pop(name, None)
        import memory_paths
        import promote_ops

        self.memory = memory_paths
        self.promote_ops = promote_ops
        self.memory.ensure_layout()
        mp = Path(self.memory.methods_personal_root())
        mp.mkdir(parents=True, exist_ok=True)
        card = mp / "share-me.md"
        card.write_text(
            "---\nid: share-me\nstrength: used\n---\n## 做法\nok\n",
            encoding="utf-8",
        )
        idx = Path(self.memory.personal_techniques_index_path())
        idx.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "entries": [
                        {
                            "id": "share-me",
                            "path": "share-me.md",
                            "triggers": ["x"],
                            "strength": "used",
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("DEV_MEMORY_ROOT", None)
        os.environ.pop("EXPERIENCE_PLUGIN_ROOT", None)

    def test_promote_copies_to_inbox_and_events(self):
        result = self.promote_ops.promote_technique("share-me", plugin_root=self.plugin)
        dest = self.plugin / "inbox-promote" / "share-me.md"
        self.assertTrue(dest.is_file())
        self.assertIn("strength: used", dest.read_text(encoding="utf-8"))
        self.assertEqual(result["path"], "inbox-promote/share-me.md")
        log = Path(self.memory.events_path())
        lines = log.read_text(encoding="utf-8").strip().splitlines()
        self.assertTrue(any('"type": "promote"' in ln or '"type":"promote"' in ln for ln in lines))

    def test_promote_rejects_hypothesis(self):
        idx = Path(self.memory.personal_techniques_index_path())
        data = json.loads(idx.read_text(encoding="utf-8"))
        data["entries"][0]["strength"] = "hypothesis"
        idx.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(SystemExit):
            self.promote_ops.promote_technique("share-me", plugin_root=self.plugin)


if __name__ == "__main__":
    unittest.main()