#!/usr/bin/env python3
import os
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]


class BannerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        os.environ["DEV_MEMORY_ROOT"] = str(self.root)
        sys.path.insert(0, str(ENGINE))
        for name in ("memory_paths", "state_ops", "habit_ops", "todo_ops", "banner"):
            sys.modules.pop(name, None)
        import state_ops
        import banner

        self.state_ops = state_ops
        self.banner = banner
        import memory_paths

        memory_paths.ensure_layout()

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("DEV_MEMORY_ROOT", None)

    def test_format_banner_off(self):
        self.state_ops.set_enabled(False)
        self.assertEqual(
            self.banner.format_banner(),
            "[experience] kb OFF · 输入 /kb-on 或 kb on 恢复",
        )

    def test_format_banner_on_includes_counts(self):
        self.state_ops.set_enabled(True)
        line = self.banner.format_banner(checkout=str(self.root))
        self.assertTrue(line.startswith("[experience] kb ON"))
        self.assertIn("习惯0", line)
        self.assertIn("逾期0", line)
        self.assertLessEqual(len(line), 200)


if __name__ == "__main__":
    unittest.main()