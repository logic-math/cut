#!/bin/bash
# install.sh — 将 cut 技能包安装到 Claude Code（软链接模式）
#
# 软链接模式：~/.claude/skills/cut → 本仓库的 cut/ 目录
# 好处：本地修改源码立即生效，无需重新安装。

set -e

SKILL_NAME="cut"
SKILL_DIR="$HOME/.claude/skills/$SKILL_NAME"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CUT_DIR="$SCRIPT_DIR/cut"

echo "Installing $SKILL_NAME skill to Claude Code (symlink mode)..."
echo "  Source : $CUT_DIR"
echo "  Target : $SKILL_DIR"
echo ""

# 检查源目录
if [ ! -f "$CUT_DIR/SKILL.md" ]; then
  echo "Error: $CUT_DIR/SKILL.md not found. Run this script from the project root."
  exit 1
fi

# 如果目标已存在（旧的复制版），先删除
if [ -e "$SKILL_DIR" ] || [ -L "$SKILL_DIR" ]; then
  echo "Removing existing installation at $SKILL_DIR ..."
  rm -rf "$SKILL_DIR"
fi

# 创建父目录
mkdir -p "$(dirname "$SKILL_DIR")"

# 创建软链接
ln -s "$CUT_DIR" "$SKILL_DIR"
echo "✓ Symlink created: $SKILL_DIR → $CUT_DIR"

# 安装 Python 依赖
echo ""
echo "Installing Python dependencies..."

# 优先用 manim venv（~/manim-env），否则 fallback 到系统 pip
MANIM_PYTHON="$HOME/manim-env/bin/python3.12"
MANIM_PIP="$HOME/manim-env/bin/pip"

if [ -f "$MANIM_PYTHON" ]; then
  echo "  Found ~/manim-env, installing manim dependencies..."
  PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig" \
    "$MANIM_PIP" install manim "manim-voiceover[edge]" edge-tts setuptools \
    PyYAML cairosvg jsonschema --quiet 2>/dev/null \
    && echo "✓ Manim dependencies installed in ~/manim-env" \
    || echo "⚠ Some manim packages failed — run manually in ~/manim-env"
  # setuptools<71 for pkg_resources compatibility
  "$MANIM_PIP" install "setuptools<71" --quiet 2>/dev/null || true
else
  echo "  ~/manim-env not found. To use Manim pipeline, create it first:"
  echo "    python3.12 -m venv ~/manim-env"
  echo "    ~/manim-env/bin/pip install manim manim-voiceover edge-tts"
fi

# 系统级依赖（非 Manim pipeline 也需要）
pip3 install PyYAML edge-tts cairosvg jsonschema --quiet --break-system-packages 2>/dev/null \
  || pip3 install PyYAML edge-tts cairosvg jsonschema --quiet 2>/dev/null \
  || echo "⚠ System pip install failed — some features may not work"

# 检查 FFmpeg
if command -v ffmpeg &>/dev/null; then
  echo "✓ FFmpeg found ($(ffmpeg -version 2>&1 | head -1 | cut -d' ' -f3))"
else
  echo "⚠ FFmpeg not found — install with: brew install ffmpeg"
fi

# 检查 manim CLI
if [ -f "$HOME/manim-env/bin/manim" ]; then
  echo "✓ Manim found ($("$HOME/manim-env/bin/manim" --version 2>/dev/null || echo 'version unknown'))"
else
  echo "⚠ Manim not found in ~/manim-env"
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
echo ""
echo "Default pipeline: Manim CE + manim-voiceover + edge-tts"
echo "  Manim python: $MANIM_PYTHON"
echo "  Manim CLI:    $HOME/manim-env/bin/manim"
