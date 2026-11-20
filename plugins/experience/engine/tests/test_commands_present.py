#!/usr/bin/env python3
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
COMMANDS = PLUGIN / "commands"


class CommandsPresentTests(unittest.TestCase):
    def test_kb_slash_commands_present(self):
        files = sorted(COMMANDS.glob("kb-*.md"))
        self.assertGreaterEqual(len(files), 10, f"expected >=10 kb-*.md under {COMMANDS}")
        for name in (
            "kb-note.md",
            "kb-deposit.md",
            "kb-doctor.md",
            "kb-help.md",
            "kb-off.md",
            "kb-on.md",
            "kb-ls.md",
            "kb-show.md",
        ):
            self.assertTrue((COMMANDS / name).is_file(), f"missing {name}")


if __name__ == "__main__":
    unittest.main()