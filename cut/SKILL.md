---
name: cut
version: "0.1.0"
description: 将文字讲稿转化为视频。当用户提到"把讲稿/文章做成视频"、"生成视频脚本"、"合成视频"、"视频制作流水线"、"cut 技能包"时使用。执行完整流水线：讲稿 → 视听脚本 → TTS 旁白 → 素材搜索/生成 → 人工审核 → FFmpeg 合成 → 最终 MP4。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# cut — AI 视频生产技能包

## 你的任务

用户想把一篇文字讲稿制作成视频。**在执行任何流水线步骤之前，先完成环境检测和配置引导。**

---

## 阶段一：环境与配置检测（每次必做）

### 1. 运行环境检测

```bash
SKILL_DIR="$HOME/.claude/skills/cut"
python3 "$SKILL_DIR/scripts/check_env.py"
```

如果有 `✗` 报错，停下来引导用户按提示安装缺失依赖，全部通过后再继续。

### 2. 读取当前配置

```bash
cat "$SKILL_DIR/cut-config.yaml"
```

### 3. 检测已配置的 API Key

```bash
echo "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:+已设置}"
echo "OPENAI_API_KEY=${OPENAI_API_KEY:+已设置}"
echo "PEXELS_API_KEY=${PEXELS_API_KEY:+已设置}"
echo "PIXABAY_API_KEY=${PIXABAY_API_KEY:+已设置}"
echo "JAMENDO_API_KEY=${JAMENDO_API_KEY:+已设置}"
echo "RUNWAY_API_KEY=${RUNWAY_API_KEY:+已设置}"
echo "ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY:+已设置}"
```

### 4. 向用户展示配置状态并询问意愿

根据检测结果，向用户展示一张配置状态表，格式如下：

```
当前配置状态：

功能              状态        说明
────────────────────────────────────────────────────────
脚本生成 (TTS)    ✓ 可用      edge-tts（免费，无需 Key）
脚本生成 (AI)     ✗ 未配置    需要 ANTHROPIC_API_KEY（更高质量）
图片素材搜索      ✗ 未配置    需要 PEXELS_API_KEY 或 PIXABAY_API_KEY
音乐素材搜索      ✗ 未配置    需要 JAMENDO_API_KEY
AI 图片生成       ✗ 未配置    需要 OPENAI_API_KEY
AI 视频生成       ✗ 未配置    需要 RUNWAY_API_KEY
手绘图生成        ✓ 可用      纯 Python，无需 Key
视频合成          ✓ 可用      FFmpeg，无需 Key
```

然后询问：
> "以上是当前配置状态。没有配置的功能会跳过或使用免费替代方案。
> 是否需要现在配置某些 API Key？还是直接用现有配置开始制作？"

### 5. 如果用户想配置 API Key

逐项引导，对每个用户想配置的 Key：

1. 告知获取地址（见下方"API Key 获取地址"）
2. 用户提供 Key 后，引导写入 shell 配置文件：

```bash
# 写入 ~/.zshrc 或 ~/.bashrc（持久化）
echo 'export ANTHROPIC_API_KEY="用户提供的key"' >> ~/.zshrc
source ~/.zshrc
```

3. 验证生效：
```bash
echo $ANTHROPIC_API_KEY
```

**API Key 获取地址：**

| Key | 获取地址 | 费用 |
|-----|---------|------|
| `ANTHROPIC_API_KEY` | console.anthropic.com | 按用量付费 |
| `OPENAI_API_KEY` | platform.openai.com | 按用量付费 |
| `PEXELS_API_KEY` | pexels.com/api | 免费 |
| `PIXABAY_API_KEY` | pixabay.com/api | 免费 |
| `JAMENDO_API_KEY` | developer.jamendo.com | 免费 |
| `RUNWAY_API_KEY` | runwayml.com | 按用量付费 |
| `ELEVENLABS_API_KEY` | elevenlabs.io | 免费额度+付费 |

### 6. 如果用户想修改服务商配置

读取并展示 `cut-config.yaml` 的关键配置项，询问是否需要修改：

- **TTS 语音**：当前 `tts.voice`，可改为其他 edge-tts 语音（如 `zh-CN-YunxiNeural` 男声）
- **视频分辨率**：当前 `output.default_resolution`
- **图片生成服务商**：当前 `image_generation.provider`

用户确认修改后，直接编辑 `$SKILL_DIR/cut-config.yaml` 对应字段。

---

## 阶段二：执行流水线

配置确认完成后，开始执行。**每步完成后向用户确认再继续。**

### Step 1：确认输入

询问用户：
1. 讲稿文件路径（Markdown 或纯文本）
2. 项目名称（默认取文件名）
3. 输出目录（默认 `./workspace`）

### Step 2：生成视听脚本

```bash
python3 "$SKILL_DIR/skills/draft-script/scripts/draft_script.py" \
  --input <讲稿路径> \
  --project <项目名> \
  --workspace-base <输出目录>
```

完成后读取 `script_preview.md` 展示场景列表给用户，询问是否满意。

### Step 3：生成 TTS 旁白

```bash
python3 "$SKILL_DIR/skills/gen-assets/scripts/gen_tts.py" \
  --script <script.json路径> \
  --workspace <workspace目录>
```

### Step 4：搜索素材（有 PEXELS/PIXABAY Key 时执行）

```bash
python3 "$SKILL_DIR/skills/fetch-assets/scripts/fetch_assets.py" <script.json路径>
```

无 Key 时告知用户跳过，后续合成将使用黑色填充帧代替视频素材。

### Step 5：生成 AI 素材

```bash
# 手绘图（始终可用，无需 Key）
python3 "$SKILL_DIR/skills/gen-assets/scripts/gen_handraw.py" \
  --script <script.json路径> --workspace <workspace目录>

# AI 图片（有 OPENAI_API_KEY 时执行）
python3 "$SKILL_DIR/skills/gen-assets/scripts/gen_image.py" \
  --script <script.json路径> --workspace <workspace目录>
```

### Step 6：素材审核（可选）

```bash
python3 "$SKILL_DIR/skills/review-assets/scripts/generate_review.py" <script.json路径>
```

生成 `review.html`，告知用户在浏览器打开审核，保存后继续。

### Step 7：合成最终视频

```bash
python3 "$SKILL_DIR/skills/compose-video/scripts/compose.py" \
  <script.json路径> \
  --output <workspace目录>/output/final.mp4 \
  --resolution 1280x720 \
  --fps 24 \
  --no-interactive
```

完成后展示输出路径，并用 `ffprobe` 显示视频时长和分辨率。

---

## 关键路径

- **skill 根目录**: `~/.claude/skills/cut/`
- **配置文件**: `~/.claude/skills/cut/cut-config.yaml`
- **环境检测**: `scripts/check_env.py`
- **讲稿转脚本**: `skills/draft-script/scripts/draft_script.py`
- **TTS 旁白**: `skills/gen-assets/scripts/gen_tts.py`
- **素材搜索**: `skills/fetch-assets/scripts/fetch_assets.py`
- **手绘图**: `skills/gen-assets/scripts/gen_handraw.py`
- **AI 图片**: `skills/gen-assets/scripts/gen_image.py`
- **审核页面**: `skills/review-assets/scripts/generate_review.py`
- **视频合成**: `skills/compose-video/scripts/compose.py`

## pipeline_state 状态

| 状态 | 含义 |
|------|------|
| `draft` | 脚本已生成 |
| `assets_fetched` | 素材搜索完成 |
| `tts_done` | TTS 旁白完成 |
| `assets_reviewed` | 素材审核完成 |
| `composed` | 视频合成完成 |

如果用户想从中间某步继续，读取 `script.json` 的 `pipeline_state` 判断从哪里接着执行。
