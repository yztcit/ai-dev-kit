#!/usr/bin/env python3
import os
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]


class StateAndLayoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        os.environ["DEV_MEMORY_ROOT"] = str(self.root)
        sys.path.insert(0, str(ENGINE))
        for name in ("memory_paths", "state_ops"):
            sys.modules.pop(name, None)
        import memory_paths
        import state_ops

        self.memory = memory_paths
        self.state_ops = state_ops

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("DEV_MEMORY_ROOT", None)

    def test_layout_and_toggle(self):
        self.memory.ensure_layout()
        self.assertTrue(Path(self.memory.todos_root()).is_dir())
        self.assertTrue(Path(self.memory.habits_root()).is_dir())
        self.assertTrue(Path(self.memory.state_path()).is_file())
        self.assertEqual(self.memory.PRODUCT_VERSION, "0.3.0")
        self.assertTrue(self.state_ops.is_enabled())
        self.state_ops.set_enabled(False)
        self.assertFalse(self.state_ops.is_enabled())


if __name__ == "__main__":
    unittest.main()