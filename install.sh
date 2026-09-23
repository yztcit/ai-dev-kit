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

echo ""
echo "========================================"
echo "  完成"
echo "========================================"
echo "重启 Claude Code 会话后生效；用 /context 可确认规则已加载。"
