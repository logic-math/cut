# cut — AI 视频生产技能包

`cut` 是一个模块化的 AI 视频生产工具包，将文字讲稿转化为最终视频，支持 AI 素材生成、人工审核、FFmpeg 合成全流程。

## 快速上手（5分钟示例）

### 1. 环境检测

```bash
python cut/scripts/check_env.py
```

确认输出中包含：
- `✓ FFmpeg OK`（否则运行 `brew install ffmpeg`）
- `✓ cairosvg OK`（否则运行 `pip install cairosvg`）
- `✓ edge-tts OK`（否则运行 `pip install edge-tts`）

### 2. 准备讲稿

将你的讲稿保存为 Markdown 文件，例如 `examples/programmer_extinction.md`。

### 3. 生成视听脚本

```bash
python cut/skills/draft-script/scripts/draft_script.py \
  --input examples/programmer_extinction.md \
  --project programmer_extinction \
  --workspace-base workspace
```

输出：`workspace/programmer_extinction/<timestamp>/script.json`

> **无 API Key 时**：自动使用 mock 模式生成脚本，可用于测试流水线。
> **有 ANTHROPIC_API_KEY 时**：调用 Claude API 生成高质量脚本。

### 4. 搜索素材

```bash
python cut/skills/fetch-assets/scripts/fetch_assets.py \
  workspace/programmer_extinction/<timestamp>/script.json
```

需要配置 API Key（可选，无 key 时跳过）：
- `PEXELS_API_KEY`：视频/图片搜索
- `JAMENDO_API_KEY`：音乐搜索

### 5. 生成 AI 素材

```bash
# 生成 TTS 旁白
python cut/skills/gen-assets/scripts/gen_tts.py \
  --script workspace/programmer_extinction/<timestamp>/script.json \
  --workspace workspace/programmer_extinction/<timestamp>

# 生成 handraw 手绘图（无需 API Key）
python cut/skills/gen-assets/scripts/gen_handraw.py \
  --script workspace/programmer_extinction/<timestamp>/script.json \
  --workspace workspace/programmer_extinction/<timestamp>

# 生成 AI 图片（需要 OPENAI_API_KEY）
python cut/skills/gen-assets/scripts/gen_image.py \
  --script workspace/programmer_extinction/<timestamp>/script.json \
  --workspace workspace/programmer_extinction/<timestamp>
```

### 6. 审核素材（可选）

```bash
python cut/skills/review-assets/scripts/generate_review.py \
  workspace/programmer_extinction/<timestamp>/script.json
```

在浏览器中打开生成的 `review.html`，选择每个场景的素材并保存。

### 7. 合成最终视频

```bash
python cut/skills/compose-video/scripts/compose.py \
  workspace/programmer_extinction/<timestamp>/script.json \
  --output workspace/programmer_extinction/output/final.mp4 \
  --resolution 1280x720 \
  --fps 24 \
  --no-interactive
```

## 完整示例

使用《程序员消亡史》示例讲稿运行完整流水线：

```bash
# Step 1: 检查环境
python cut/scripts/check_env.py

# Step 2: 生成脚本（mock 模式，无需 API Key）
python cut/skills/draft-script/scripts/draft_script.py \
  --input examples/programmer_extinction.md \
  --project programmer_extinction \
  --workspace-base workspace

# Step 3: 生成 TTS 旁白（需要网络，使用免费 edge-tts）
python cut/skills/gen-assets/scripts/gen_tts.py \
  --script workspace/programmer_extinction/<timestamp>/script.json \
  --workspace workspace/programmer_extinction/<timestamp>

# Step 4: 合成视频
python cut/skills/compose-video/scripts/compose.py \
  workspace/programmer_extinction/<timestamp>/script.json \
  --output workspace/programmer_extinction/output/final.mp4 \
  --resolution 1280x720 \
  --no-interactive
```

验证输出：

```bash
ffprobe -v quiet -print_format json -show_format workspace/programmer_extinction/output/final.mp4
```

## 配置

编辑 `cut/cut-config.yaml` 配置各服务商：

```yaml
tts:
  provider: edge_tts  # edge_tts | openai | elevenlabs

image_generation:
  provider: dalle3    # dalle3 | stable_diffusion

video_generation:
  provider: runway    # runway

handraw:
  chart_provider: svg_python   # svg_python (无需 API Key)
  illus_provider: dalle3       # dalle3
```

## 环境依赖

| 依赖 | 用途 | 安装方式 |
|------|------|----------|
| FFmpeg | 视频合成（必须） | `brew install ffmpeg` |
| Python 3.9+ | 运行脚本（必须） | 系统自带或 pyenv |
| edge-tts | 免费 TTS | `pip install edge-tts` |
| cairosvg | SVG 转 PNG | `pip install cairosvg` |
| PyYAML | 配置解析 | `pip install PyYAML` |
| anthropic | Claude API（可选） | `pip install anthropic` |
| openai | DALL-E/GPT（可选） | `pip install openai` |

## 子技能说明

| 技能 | 路径 | 功能 |
|------|------|------|
| draft-script | `cut/skills/draft-script/` | 讲稿转视听脚本 JSON |
| fetch-assets | `cut/skills/fetch-assets/` | 搜索股票视频/图片/音乐 |
| gen-assets | `cut/skills/gen-assets/` | AI 生成素材（TTS/图片/视频/手绘） |
| review-assets | `cut/skills/review-assets/` | 交互式 HTML 素材审核 |
| compose-video | `cut/skills/compose-video/` | FFmpeg 视频合成 |

## 常见问题

**Q: 没有任何 API Key，能跑通流水线吗？**

A: 可以。draft-script 使用 mock 模式，TTS 使用免费的 edge-tts，handraw_chart 使用纯 Python SVG 方案，compose-video 只需要 FFmpeg。

**Q: 生成的视频没有字幕怎么办？**

A: 需要 FFmpeg 编译时包含 libass。如果缺少，视频会正常生成但不含字幕。

**Q: 如何切换 TTS 语音？**

A: 在 `cut-config.yaml` 中修改 `tts.voice`，支持所有 edge-tts 语音（如 `zh-CN-YunxiNeural`）。
