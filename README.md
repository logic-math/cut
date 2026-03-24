# cut — AI 视频生产技能包

将文字讲稿一键转化为视频。输入 Markdown 讲稿，输出 MP4 视频。

```
讲稿(.md) → 视听脚本(JSON) → 素材搜索/生成 → 人工审核 → FFmpeg 合成 → 最终视频(.mp4)
```

---

## 安装

### 1. 系统依赖

**FFmpeg**（必须）：

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# 验证
ffmpeg -version
```

**Python 3.11+**（必须）：

```bash
python3 --version  # 确认 ≥ 3.11
```

### 2. Python 依赖

```bash
pip install PyYAML edge-tts cairosvg jsonschema
```

可选依赖（按需安装）：

```bash
pip install anthropic   # 用 Claude API 生成高质量脚本
pip install openai      # 用 DALL-E 3 生成图片
```

### 3. 克隆项目

```bash
git clone <repo-url>
cd cut
```

### 4. 验证安装

```bash
python3 cut/scripts/check_env.py
```

正常输出：

```
✓ Python 3.11 OK
✓ FFmpeg OK
✓ cairosvg OK
✓ edge-tts OK
✓ PyYAML OK
```

---

## 快速开始

以下示例使用内置的《程序员消亡史》讲稿，**无需任何 API Key** 即可跑通完整流水线。

### Step 1：生成视听脚本

```bash
python3 cut/skills/draft-script/scripts/draft_script.py \
  --input examples/programmer_extinction.md \
  --project my_video \
  --workspace-base workspace
```

输出：`workspace/my_video/<timestamp>/script.json`（含分镜、旁白、画面描述）

> 有 `ANTHROPIC_API_KEY` 时调用 Claude 生成高质量脚本；无 key 时自动使用 mock 模式。

### Step 2：生成 TTS 旁白

```bash
python3 cut/skills/gen-assets/scripts/gen_tts.py \
  --script workspace/my_video/<timestamp>/script.json \
  --workspace workspace/my_video/<timestamp>
```

默认使用免费的 edge-tts，无需 API Key，需要网络连接。

### Step 3：搜索素材（可选）

```bash
python3 cut/skills/fetch-assets/scripts/fetch_assets.py \
  workspace/my_video/<timestamp>/script.json
```

> 需要配置 `PEXELS_API_KEY` 或 `JAMENDO_API_KEY`，无 key 时跳过。

### Step 4：审核素材（可选）

```bash
python3 cut/skills/review-assets/scripts/generate_review.py \
  workspace/my_video/<timestamp>/script.json
```

在浏览器中打开生成的 `review.html`，为每个场景选择素材，点击保存。

### Step 5：合成视频

```bash
python3 cut/skills/compose-video/scripts/compose.py \
  workspace/my_video/<timestamp>/script.json \
  --output workspace/my_video/output/final.mp4 \
  --resolution 1280x720 \
  --no-interactive
```

输出：`workspace/my_video/output/final.mp4`

---

## 配置 API Key

编辑 `cut/cut-config.yaml` 并设置环境变量：

| 服务 | 环境变量 | 用途 |
|------|---------|------|
| Claude | `ANTHROPIC_API_KEY` | 生成高质量视听脚本 |
| DALL-E 3 | `OPENAI_API_KEY` | AI 图片生成、手绘插图 |
| Runway | `RUNWAY_API_KEY` | AI 视频生成 |
| Pexels | `PEXELS_API_KEY` | 搜索库存视频/图片（免费注册） |
| Jamendo | `JAMENDO_API_KEY` | 搜索免版权音乐（免费注册） |

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export PEXELS_API_KEY=...
```

---

## 配置文件

`cut/cut-config.yaml` 控制所有服务商选择：

```yaml
tts:
  provider: edge_tts        # edge_tts（免费）| openai | elevenlabs
  voice: zh-CN-XiaoxiaoNeural

image_generation:
  provider: dalle3           # dalle3 | stable_diffusion

video_generation:
  provider: runway           # runway

stock_video:
  providers: [pexels, pixabay]

stock_image:
  providers: [pexels, pixabay]

music:
  providers: [jamendo, pixabay]

handraw:
  chart_provider: svg        # 纯 Python，无需 API Key
  illustration_provider: dalle3

output:
  default_format: mp4
  default_resolution: 1920x1080
  default_fps: 30
```

---

## 项目结构

```
cut/
├── README.md                       # 本文件
├── examples/
│   └── programmer_extinction.md    # 示例讲稿
├── workspace/                      # 运行时输出目录
└── cut/
    ├── cut-config.yaml             # 服务商配置
    ├── scripts/
    │   └── check_env.py            # 环境检测
    └── skills/
        ├── draft-script/           # 讲稿 → 视听脚本 JSON
        ├── fetch-assets/           # 搜索库存视频/图片/音乐
        ├── gen-assets/             # AI 生成 TTS/图片/视频/手绘图
        ├── review-assets/          # HTML 交互审核界面
        └── compose-video/          # FFmpeg 视频合成
```

---

## 常见问题

**Q: 没有任何 API Key，能跑通完整流水线吗？**

可以。draft-script 使用 mock 模式，TTS 使用免费的 edge-tts，handraw_chart 使用纯 Python SVG，compose-video 只需 FFmpeg。

**Q: 生成的视频没有字幕？**

macOS 默认的 FFmpeg 不含 libass，字幕烧录会自动 fallback（视频正常生成，仅无字幕）。如需字幕，可通过 Homebrew 安装含 libass 的版本。

**Q: 如何切换 TTS 语音？**

在 `cut/cut-config.yaml` 中修改 `tts.voice`，例如 `zh-CN-YunxiNeural`（男声）。可用语音列表：`edge-tts --list-voices`。

**Q: 如何添加新的 AI 服务商？**

每类服务（TTS/图像/视频）均有 Python Protocol 接口，实现接口后在 `provider_map` 中注册即可，无需修改主流程代码。详见 `cut/skills/gen-assets/scripts/providers/`。
