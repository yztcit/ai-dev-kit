#!/bin/bash
# 幂等安装器：把本仓库 health/ 的脚本挂到用户级，并注册 launchd 定时巡检。
# 换设备 = clone 仓库 + 跑本脚本。
set -euo pipefail

HEALTH_DIR="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
SCRIPTS_DIR="$HOME/.claude/scripts"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST="$LAUNCH_AGENTS_DIR/com.tal.claude.skillhealth.plist"
LABEL="com.tal.claude.skillhealth"

# 1. 用户级脚本目录：软链三个脚本到仓库（幂等）
mkdir -p "$SCRIPTS_DIR"
for f in scan_skill_usage.py scan_capability_layers.py decision_log.py skill-health-check.sh; do
  ln -sf "$HEALTH_DIR/$f" "$SCRIPTS_DIR/$f"
done
echo "✓ 脚本软链已就绪：$SCRIPTS_DIR"

# 2. 报告目录（gitignore，但本地可见）
mkdir -p "$HEALTH_DIR/report"
echo "✓ 报告目录已就绪：$HEALTH_DIR/report"

# 3. 生成 launchd plist（路径写入当前用户 + 仓库绝对路径）
mkdir -p "$LAUNCH_AGENTS_DIR"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${HEALTH_DIR}/skill-health-check.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key>
    <integer>1</integer>
    <key>Hour</key>
    <integer>9</integer>
    <key>Minute</key>
    <integer>15</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>${HEALTH_DIR}/report/run.log</string>
  <key>StandardErrorPath</key>
  <string>${HEALTH_DIR}/report/run.log</string>
</dict>
</plist>
EOF
echo "✓ plist 已生成：$PLIST"

# 4. 重载 launchd（幂等）
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "✓ launchd 任务已加载：$LABEL"

echo ""
echo "完成。换设备只需 clone 仓库后执行本脚本。"
echo "手动跑一次验证：$SCRIPTS_DIR/skill-health-check.sh"
