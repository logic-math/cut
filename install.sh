#!/bin/bash
# install.sh — 将 cut 技能包安装到 Claude Code

set -e

SKILL_NAME="cut"
SKILL_DIR="$HOME/.claude/skills/$SKILL_NAME"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CUT_DIR="$SCRIPT_DIR/cut"

echo "Installing $SKILL_NAME skill to Claude Code..."
echo "  Source : $CUT_DIR"
echo "  Target : $SKILL_DIR"
echo ""

# 检查源目录
if [ ! -f "$CUT_DIR/SKILL.md" ]; then
  echo "Error: $CUT_DIR/SKILL.md not found. Run this script from the project root."
  exit 1
fi

# 创建目标目录
mkdir -p "$SKILL_DIR"

# 复制技能包内容
rsync -a --delete "$CUT_DIR/" "$SKILL_DIR/"

echo "✓ Skill installed"

# 安装 Python 依赖
echo ""
echo "Installing Python dependencies..."
pip3 install PyYAML edge-tts cairosvg jsonschema --quiet --break-system-packages 2>/dev/null \
  || pip3 install PyYAML edge-tts cairosvg jsonschema --quiet 2>/dev/null \
  && echo "✓ Python dependencies installed" \
  || echo "⚠ pip install failed — run manually: pip install PyYAML edge-tts cairosvg jsonschema"

# 检查 FFmpeg
if command -v ffmpeg &>/dev/null; then
  echo "✓ FFmpeg found"
else
  echo "⚠ FFmpeg not found — install with: brew install ffmpeg"
fi

# 验证安装
echo ""
echo "Verifying installation..."
python3 "$SKILL_DIR/scripts/check_env.py"

echo ""
echo "Done! The /cut skill is now available in Claude Code."
echo ""
echo "Usage: In Claude Code, just say:"
echo "  '帮我把 examples/programmer_extinction.md 做成视频'"
echo "  '/cut --input my_lecture.md --project my_video'"
