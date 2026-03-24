---
name: cut
version: "0.1.0"
description: 将文字讲稿转化为视频。当用户提到"把讲稿/文章做成视频"、"生成视频脚本"、"合成视频"、"视频制作流水线"、"cut 技能包"时使用。执行完整流水线：讲稿 → 视听脚本 → TTS 旁白 → 素材搜索/生成 → 人工审核 → FFmpeg 合成 → 最终 MP4。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# cut — AI 视频生产技能包

## 你的任务

用户想把一篇文字讲稿制作成视频。按以下流水线执行，每步完成后向用户确认再继续。

## 前置检查

首先定位 cut 安装目录和项目工作目录：

```bash
# cut 安装在 ~/.claude/skills/cut/
SKILL_DIR="$HOME/.claude/skills/cut"
python3 "$SKILL_DIR/scripts/check_env.py"
```

如果环境检测有报错，先引导用户完成安装（见报错提示）。

## 执行步骤

### Step 1：确认输入

询问用户：
1. 讲稿文件路径（Markdown 格式，也可接受纯文本）
2. 项目名称（用于创建 workspace 目录，默认取文件名）
3. 输出目录（默认 `./workspace`）

### Step 2：生成视听脚本

```bash
python3 "$SKILL_DIR/scripts/draft_script.py" \
  --input <讲稿路径> \
  --project <项目名> \
  --workspace-base <输出目录>
```

完成后：
- 读取生成的 `script_preview.md` 展示给用户（场景列表、时长、旁白摘要）
- 询问用户是否满意，如需调整可修改 `script.json` 后继续

### Step 3：生成 TTS 旁白

```bash
SCRIPT_PATH="<workspace>/<project>/<timestamp>/script.json"
WORKSPACE_DIR="<workspace>/<project>/<timestamp>"

python3 "$SKILL_DIR/skills/gen-assets/scripts/gen_tts.py" \
  --script "$SCRIPT_PATH" \
  --workspace "$WORKSPACE_DIR"
```

默认使用免费的 edge-tts，无需 API Key。

### Step 4：搜索素材（可选，需要 API Key）

```bash
python3 "$SKILL_DIR/skills/fetch-assets/scripts/fetch_assets.py" "$SCRIPT_PATH"
```

如果用户没有 `PEXELS_API_KEY` 等，跳过此步。

### Step 5：生成 AI 素材（可选，需要 API Key）

```bash
# 手绘图（无需 API Key）
python3 "$SKILL_DIR/skills/gen-assets/scripts/gen_handraw.py" \
  --script "$SCRIPT_PATH" --workspace "$WORKSPACE_DIR"

# AI 图片（需要 OPENAI_API_KEY）
python3 "$SKILL_DIR/skills/gen-assets/scripts/gen_image.py" \
  --script "$SCRIPT_PATH" --workspace "$WORKSPACE_DIR"
```

### Step 6：审核素材（可选）

```bash
python3 "$SKILL_DIR/skills/review-assets/scripts/generate_review.py" "$SCRIPT_PATH"
```

生成 `review.html`，告知用户在浏览器中打开审核，选完后保存继续。

### Step 7：合成最终视频

```bash
python3 "$SKILL_DIR/skills/compose-video/scripts/compose.py" \
  "$SCRIPT_PATH" \
  --output "<workspace>/<project>/output/final.mp4" \
  --resolution 1280x720 \
  --fps 24 \
  --no-interactive
```

完成后展示输出路径和视频时长。

## 关键路径说明

- **skill 脚本根目录**: `~/.claude/skills/cut/`
- **环境检测**: `scripts/check_env.py`
- **讲稿转脚本**: `skills/draft-script/scripts/draft_script.py`
- **TTS 旁白**: `skills/gen-assets/scripts/gen_tts.py`
- **素材搜索**: `skills/fetch-assets/scripts/fetch_assets.py`
- **手绘图生成**: `skills/gen-assets/scripts/gen_handraw.py`
- **AI 图片**: `skills/gen-assets/scripts/gen_image.py`
- **审核页面**: `skills/review-assets/scripts/generate_review.py`
- **视频合成**: `skills/compose-video/scripts/compose.py`
- **服务商配置**: `cut-config.yaml`

## pipeline_state 状态

每步完成后 `script.json` 中的 `pipeline_state` 会更新：

| 状态 | 含义 |
|------|------|
| `draft` | 脚本已生成 |
| `assets_fetched` | 素材搜索完成 |
| `tts_done` | TTS 旁白完成 |
| `assets_reviewed` | 素材审核完成 |
| `composed` | 视频合成完成 |

如果用户想从中间某步继续，读取 `script.json` 的 `pipeline_state` 判断从哪里接着执行。
