#!/usr/bin/env python3
"""Static help topics for personal experience kb."""
from __future__ import annotations

TOPICS: dict[str, str] = {
    "note": "kb note --slug S --body TEXT | --body-file F\n  写入 scratch 草稿并记录 note 事件。",
    "deposit": "kb deposit-apply --file PATH\n  读取沉淀提案 JSON，校验后写入 facts / methods-personal。",
    "todo": "kb todo add --title T [--due YYYY-MM-DD]\n  kb todo done <id>\n  kb todo list [--overdue]",
    "habit": "kb habit upsert --id ID --title T --body TEXT\n  kb habit list",
    "off": "kb off\n  关闭个人经验注入（state.json enabled=false）。",
    "on": "kb on\n  重新开启经验注入。",
    "import": "kb import <检出目录> [--force]\n  把 .claude 树导入 KB base/（见分支规则）。",
    "status": "kb status [目录]\n  仓库投影状态 + 个人 enabled / 习惯数 / 逾期待办。",
    "report": "kb report [--days N] [--json]\n  事件汇总与 technique bump 候选。",
    "doctor": "kb doctor [--json]\n  安装与健康检查（off 时显示 DISABLED）。",
    "ls": (
        "kb ls <scratch|technique|habit|todo|facts> [--json] [--limit N] [--all] [--overdue]\n"
        "  只读统一表：type id title_or_slug meta path。\n"
        "  facts 默认当前仓；--all 全库。"
    ),
    "show": (
        "kb show <scratch|technique|habit|todo|facts> <id> [--full]\n"
        "  只读查看正文（默认约 80 行，--full 全文）。todo 输出 JSON。"
    ),
}


def cmd_help(argv) -> int:
    if not argv:
        print("experience kb help · 主题：")
        for key in sorted(TOPICS):
            print(f"  {key}")
        print("\n用法: kb help <主题>   完整 CLI: kb -h")
        return 0
    topic = argv[0].strip().lower()
    text = TOPICS.get(topic)
    if not text:
        print(f"未知主题: {topic}")
        print("可用:", ", ".join(sorted(TOPICS)))
        return 2
    print(f"kb {topic}\n{text}")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(cmd_help(sys.argv[1:]))