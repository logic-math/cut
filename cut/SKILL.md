---
name: cut
description: Context-First AI Coding Framework for producing video content from scripts. Orchestrates a pipeline from draft script through asset fetching/generation, human review, and final video composition.
trigger: Use this skill when you need to create a video from a text script, manage the video production pipeline, or work with any of the cut sub-skills (draft-script, fetch-assets, gen-assets, review-assets, compose-video).
version: "0.1.0"
---

# cut — AI 视频生产技能包

`cut` 是一个模块化技能包，将文字讲稿通过 AI 流水线转化为最终视频。支持 TTS 旁白、AI 图片生成、手绘图、股票视频搜索、人工审核和 FFmpeg 合成。

## Pipeline 总览

```
讲稿(文字) → [draft-script] → 视听脚本(JSON)
                                    ↓
                        人工审核确认脚本
                                    ↓
          [fetch-assets] / [gen-assets] (并行)
                                    ↓
                        [review-assets] 人工审核素材
                                    ↓
                        [compose-video]
                                    ↓
                        最终视频文件 (MP4/MOV)
```

---

## Sub-Skills 详细说明

### draft-script

**路径**: `cut/skills/draft-script/scripts/draft_script.py`

将文字讲稿转化为结构化的视听脚本 JSON，包含每个场景的旁白、字幕、画面描述、素材关键词和背景音乐建议。

**调用方式**:
```bash
python cut/skills/draft-script/scripts/draft_script.py \
  --input <讲稿.md> \
  --project <项目名> \
  --workspace-base workspace
```

**参数说明**:
- `--input`: 输入讲稿文件路径（Markdown 格式）
- `--project`: 项目名称，用于创建 workspace 目录
- `--workspace-base`: workspace 根目录（默认 `./workspace`）
- `--lang`: 语言（`zh` 或 `en`，默认 `zh`）

**输出**:
- `workspace/<project>/<timestamp>/script.json`：结构化脚本
- `workspace/<project>/<timestamp>/script_preview.md`：Markdown 预览表格

**script.json 格式**:
```json
{
  "title": "视频标题",
  "total_duration": 120,
  "output_format": "mp4",
  "resolution": "1920x1080",
  "pipeline_state": "draft",
  "scenes": [
    {
      "id": "scene_01",
      "duration": 10,
      "narration": "旁白文字",
      "subtitle": "字幕文字",
      "visual": {
        "type": "video|image|handraw_chart|handraw_illustration",
        "description": "画面描述",
        "keywords": ["english", "keywords"],
        "status": "pending",
        "asset_path": null
      },
      "audio": {
        "narration_status": "pending",
        "narration_path": null,
        "music": {
          "keywords": ["mood:calm", "genre:ambient"],
          "volume": 0.3
        }
      }
    }
  ]
}
```

**API Key 配置**:
- `ANTHROPIC_API_KEY`：调用 Claude API 生成高质量脚本
- 无 key 时：自动使用 mock 模式（基于文本切分）

---

### fetch-assets

**路径**: `cut/skills/fetch-assets/scripts/fetch_assets.py`

从股票素材平台搜索视频、图片和音乐候选，填充 `script.json` 中每个场景的 `candidates` 字段。

**调用方式**:
```bash
python cut/skills/fetch-assets/scripts/fetch_assets.py <script.json>
```

**支持的 Provider**:

| 类型 | Provider | API Key 环境变量 | 获取地址 |
|------|----------|-----------------|---------|
| 视频/图片 | Pexels | `PEXELS_API_KEY` | pexels.com/api |
| 视频/图片 | Pixabay | `PIXABAY_API_KEY` | pixabay.com/api |
| 音乐 | Jamendo | `JAMENDO_API_KEY` | developer.jamendo.com |

**Fallback 机制**: Pexels 无结果时自动 fallback 到 Pixabay。

**音乐关键词格式**:
```
mood:melancholic    # 情绪标签
genre:ambient       # 风格标签
```

**输出**: 更新 `script.json` 中每个场景的 `visual.candidates` 和 `audio.music.candidates`。

---

### gen-assets

**路径**: `cut/skills/gen-assets/scripts/`

生成 AI 素材，包括 TTS 旁白音频、AI 图片、AI 视频和手绘图。

#### gen_tts.py — TTS 旁白生成

```bash
python cut/skills/gen-assets/scripts/gen_tts.py \
  --script <script.json> \
  --workspace <workspace_dir> \
  --provider edge_tts
```

**支持的 TTS Provider**:

| Provider | 配置名 | API Key | 特点 |
|----------|--------|---------|------|
| edge-tts | `edge_tts` | 无需 | 免费，支持中英文 |
| OpenAI TTS | `openai` | `OPENAI_API_KEY` | 高质量，收费 |
| ElevenLabs | `elevenlabs` | `ELEVENLABS_API_KEY` | 最高质量，收费 |

**输出**: 在 `workspace/assets/narration/` 生成 MP3 文件，更新 `audio.narration_path`。

#### gen_image.py — AI 图片生成

```bash
python cut/skills/gen-assets/scripts/gen_image.py \
  --script <script.json> \
  --workspace <workspace_dir>
```

**支持的 Provider**:
- `dalle3`：DALL-E 3（需要 `OPENAI_API_KEY`）
- `stable_diffusion`：Stability AI（需要 `STABILITY_API_KEY`）

#### gen_handraw.py — 手绘图生成

```bash
python cut/skills/gen-assets/scripts/gen_handraw.py \
  --script <script.json> \
  --workspace <workspace_dir>
```

**两种手绘类型**:
- `handraw_chart`：数据图表，使用 SVG 纯 Python 方案（**无需 API Key**）
- `handraw_illustration`：概念插画，使用 DALL-E 3（需要 `OPENAI_API_KEY`）

**SVG 方案特点**: 使用 `cairosvg` 将 SVG 转换为 PNG，无需 Node.js，无需 API Key。

#### gen_video.py — AI 视频生成

```bash
python cut/skills/gen-assets/scripts/gen_video.py \
  --script <script.json> \
  --workspace <workspace_dir>
```

**支持的 Provider**:
- `runway`：Runway ML（需要 `RUNWAY_API_KEY`）

---

### review-assets

**路径**: `cut/skills/review-assets/scripts/generate_review.py`

生成交互式 HTML 审核页面，让用户在浏览器中选择每个场景的最佳素材。

**调用方式**:
```bash
python cut/skills/review-assets/scripts/generate_review.py <script.json>
```

**功能**:
- 展示每个场景的所有候选素材（视频/图片/音频预览）
- 支持手动选择 `selected_candidate`
- 支持标记"AI 生成"状态（`generating: true`）
- 保存时更新 `script.json` 中的 `status` 和 `pipeline_state`

**两种审核模式**:
1. **服务器模式**：通过 POST `/save_script` 直接写回 `script.json`
2. **纯静态模式**：通过浏览器下载更新后的 `script.json`（无需服务器）

---

### compose-video

**路径**: `cut/skills/compose-video/scripts/compose.py`

使用 FFmpeg 将所有审核通过的素材合成为最终视频。

**调用方式**:
```bash
python cut/skills/compose-video/scripts/compose.py <script.json> \
  --output <output.mp4> \
  --resolution 1280x720 \
  --fps 24 \
  --format mp4 \
  --music-volume 0.3 \
  --no-interactive
```

**参数说明**:
- `--resolution`: `720p` / `1080p` / `4K` / `WxH`（默认交互询问）
- `--fps`: 帧率，24 或 30（默认交互询问）
- `--format`: `mp4` 或 `mov`（默认交互询问）
- `--music-volume`: 背景音乐音量 0.0-1.0（默认 0.3）
- `--no-interactive`: 使用默认值，不交互询问

**视频素材处理逻辑**:
- `video`：clip 短于场景时长 → 循环（`-stream_loop -1`）；长于场景时长 → 截取中间段（跳过前 10%）
- `image`：Ken Burns 缓慢放大效果
- `handraw`：fade-in 淡入 + 缓慢放大效果
- 无素材：黑色填充帧

**音频处理**:
- 旁白（主轨）+ 背景音乐（`volume` 衰减）通过 `amix` 混合
- 无素材时生成静音轨

**字幕**:
- 生成 SRT 文件并通过 `subtitles` 滤镜烧录（需要 FFmpeg 含 libass）

**输出**: 更新 `script.json` 中 `pipeline_state = "composed"`。

---

## 配置文件

编辑 `cut/cut-config.yaml`：

```yaml
tts:
  provider: edge_tts
  voice: zh-CN-XiaoxiaoNeural
  output_format: mp3

image_generation:
  provider: dalle3
  size: "1792x1024"
  quality: standard

video_generation:
  provider: runway
  duration: 4

handraw:
  chart_provider: svg_python
  illus_provider: dalle3

output:
  default_resolution: "1280x720"
  default_fps: 24
  default_format: mp4
```

---

## 环境检测

```bash
python cut/scripts/check_env.py
```

检测项目：Python 版本、FFmpeg、cairosvg、PyYAML、edge-tts、openai、anthropic。

---

## Pipeline State 流转

```
draft → assets_fetched → assets_generated → assets_reviewed → composed
```

每个 skill 完成后会更新 `script.json` 中的 `pipeline_state`，确保流水线状态可追踪。
