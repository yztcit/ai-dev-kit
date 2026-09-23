#!/bin/bash
# 新机器一键安装：把本仓库的资产挂到用户级。幂等，可重复执行。
#
# 适用范围：**你自己的机器**。给他人用请走插件分发（`/plugin install`），
# 见 README「两种交付方式」。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
echo "========================================"
echo "  ai-dev-kit 本机安装"
echo "  仓库：$REPO_ROOT"
echo "========================================"
echo ""

# --- 1. health：巡检脚本 + launchd 定时任务 ---
if [ -x "$REPO_ROOT/health/install.sh" ]; then
  bash "$REPO_ROOT/health/install.sh"
else
  echo "⚠️  未找到可执行的 health/install.sh，跳过"
fi

# --- 2. conventions：用户级规则 ---
# 交付方式：软链到用户级 rules（原生加载，声明式，无执行）。
# 与 plugins/conventions 插件是**同一份内容**——插件面向分发，规则面向本机。
# ⚠️ 不要同时启用插件与规则，否则同一内容加载两遍。
RULES_DIR="$HOME/.claude/rules"
mkdir -p "$RULES_DIR"
ln -sf "$REPO_ROOT/plugins/conventions/CONVENTIONS.md" "$RULES_DIR/conventions.md"
echo "✓ 用户级规则已就绪：$RULES_DIR/conventions.md"

# --- 3. health 命令：状态一览入口 ---
# 放在 ~/.local/bin（已在 PATH；uv/graphify 等也在此，与本工具依赖同处）。
# 装了它就能在任何地方直接跑 `health`，不必记路径、也不必问 Claude。
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
ln -sf "$REPO_ROOT/status.sh" "$BIN_DIR/health"
echo "✓ 命令已就绪：$BIN_DIR/health"
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) echo "  ⚠️  $BIN_DIR 不在 PATH，需自行加入 shell 配置" ;;
esac

echo ""
echo "========================================"
echo "  完成"
echo "========================================"
echo "重启 Claude Code 会话后生效；用 /context 可确认规则已加载。"
echo "随时用 \`health\` 看体系状态（-v 展开明细）。"
