#!/bin/bash
# 安装 shared-config：注册 SessionStart hook（自动对齐）+ 用户级 skill（可点名配置）。幂等。
set -euo pipefail

DIR="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
echo "── shared-config"

# --- 1. SessionStart hook：会话开始时把当前检出的 .claude 与同仓库其它检出对齐 ---
# 这是「忘记跑脚本」的正解：由 harness 执行，不依赖人记。
python3 - "$DIR/sync.py" <<'PY'
import json, os, shutil, sys

sync_py = sys.argv[1]
settings = os.path.expanduser("~/.claude/settings.json")
# 不加 --quiet：脚本平时静默，只在「刚做了快进」或「有分歧需人汇总」时输出
cmd = f'python3 "{sync_py}"'

data = {}
if os.path.isfile(settings):
    with open(settings, encoding="utf-8") as f:
        data = json.load(f)
    shutil.copy2(settings, settings + ".bak-shared-config")

entries = data.setdefault("hooks", {}).setdefault("SessionStart", [])
before = json.dumps(entries, ensure_ascii=False, sort_keys=True)


# 清掉本插件的历史 hook（早期软链方案 link.py、以及 sync.py 的旧参数版本），
# 避免同一次会话里跑两遍。判据是「指向本插件但不是当前命令」。
def is_stale(h):
    c = h.get("command", "")
    return "shared-config/" in c and c != cmd


for e in entries:
    e["hooks"] = [h for h in e.get("hooks", []) if not is_stale(h)]
entries = [e for e in entries if e.get("hooks")]

if not any(h.get("command") == cmd for e in entries for h in e.get("hooks", [])):
    entries.append({"hooks": [{"type": "command", "command": cmd}]})
data["hooks"]["SessionStart"] = entries

# 有变化就落盘——只判「命令是否已存在」会漏掉清理动作（清理过但没写回）
if json.dumps(entries, ensure_ascii=False, sort_keys=True) != before:
    os.makedirs(os.path.dirname(settings), exist_ok=True)
    with open(settings, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"✓ SessionStart hook 已就绪：{settings}")
    print(f"  命令：{cmd}")
else:
    print("✓ SessionStart hook 已注册（无需改动）")
PY

# --- 2. 用户级 skill：想显式配置/汇总时点名用 ---
# 与 health 的 `health` 命令同理：装在用户级，任何项目里都能用，不必记仓库路径。
SKILL_DIR="$HOME/.claude/skills/shared-config"
mkdir -p "$SKILL_DIR"
ln -sf "$DIR/SKILL.md" "$SKILL_DIR/SKILL.md"
echo "✓ 用户级 skill 已就绪：$SKILL_DIR/SKILL.md"
