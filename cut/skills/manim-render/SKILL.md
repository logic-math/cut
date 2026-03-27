# manim-render — Manim CE 动画渲染模块

将 script.json 转换为 Manim CE Python 代码，并批量渲染为 MP4 视频。

## 脚本说明

### gen_manim_code.py
将 script.json 中的场景数据生成 Manim CE Python 代码框架。

**用法：**
```bash
python3 scripts/gen_manim_code.py \
  --script path/to/script.json \
  --output path/to/scenes.py \
  --config path/to/cut-config.yaml
```

**生成的代码特点：**
- 每个场景继承 `VoiceoverScene`
- TTS 服务由 `cut-config.yaml` 中的 `tts.provider` 决定
  - `fish_audio` → `FishAudioService`（推荐，音色克隆）
  - `edge_tts` → `EdgeTTSService`（免费备用）
  - `openai` → `OpenAITTSService`
- 场景类型映射：
  - `handraw_chart` → 图表/时间轴/对比图动画
  - `handraw_illustration` → 示意图/流程图动画
  - `video` / `image` → 文字动画 + 背景效果

**生成后 Claude 会直接改写 scenes.py**，为每个场景填充真实内容。

---

### render_manim.py
批量渲染所有 Manim 场景并用 FFmpeg 合并为最终 MP4。

**用法：**
```bash
python3 scripts/render_manim.py \
  --script path/to/script.json \
  --manim-file path/to/scenes.py \
  --output path/to/final.mp4 \
  --config path/to/cut-config.yaml \
  [--quality h]     # l/m/h/k，默认读 config
  [--scenes Scene01 Scene02]  # 只渲染指定场景
```

**渲染质量对应分辨率：**
| quality | 分辨率 | 帧率 |
|---------|--------|------|
| `l` | 480p | 15fps |
| `m` | 720p | 30fps |
| `h` | 1080p | 60fps（默认）|
| `k` | 2160p | 60fps |

## 依赖

- `~/manim-env/bin/manim`（Manim CE v0.18+）
- `manim-voiceover`（含 TTS 服务适配器）
- `ffmpeg`（合并视频用）
- `fish-audio-sdk`（使用 fish_audio provider 时需要）

## 安装

```bash
# 创建 Python 3.12 venv（避免 3.14 兼容性问题）
python3.12 -m venv ~/manim-env

# 安装 Manim 套件
PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig" \
  ~/manim-env/bin/pip install manim manim-voiceover edge-tts
~/manim-env/bin/pip install "setuptools<71"

# 安装 Fish Audio SDK（可选，使用 fish_audio provider 时）
~/manim-env/bin/pip install fish-audio-sdk
```
