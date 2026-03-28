---
name: cut
slug: cut
version: "0.2.0"
description: 将文字讲稿转化为视频。当用户提到"把讲稿/文章做成视频"、"生成视频脚本"、"合成视频"、"视频制作"、"cut 技能"时使用。使用 Manim CE + manim-voiceover + Fish Audio / edge-tts 生成动画讲解视频。
---

# cut — AI 视频生产技能包（OpenClaw 版）

> 本文件是 cut 技能的 **OpenClaw 专属指令**，使用 OpenClaw 工具集（exec/read/write/edit）。
> Claude Code 版指令见同仓库 `cut/SKILL.md`。

## 核心路径

```
SKILL_DIR = ~/.claude/skills/cut        # cut 技能根目录（symlink 到源码）
CUT_REPO  = ~/AICODING/CREATION/cut    # 源码仓库
CONFIG    = ~/.claude/skills/cut/cut-config.yaml
```

---

## 阶段一：环境与配置检测（每次必做）

### 1. 运行环境检测

```bash
python3 ~/.claude/skills/cut/scripts/check_env.py
```

如有 `✗` 报错，停下来引导用户安装缺失依赖，全部通过后再继续。

### 2. 读取当前配置

```bash
cat ~/.claude/skills/cut/cut-config.yaml
```

重点关注 `pipeline`（`manim` 或 `ffmpeg`）和 `tts.provider`。

### 3. 检测 Manim 环境 & API Keys

```bash
ls ~/manim-env/bin/manim 2>/dev/null && echo "✓ Manim 已安装" || echo "✗ Manim 未安装"
~/manim-env/bin/manim --version 2>/dev/null || true
echo "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:+已设置}"
echo "FISH_AUDIO_API_KEY=${FISH_AUDIO_API_KEY:+已设置}"
echo "OPENAI_API_KEY=${OPENAI_API_KEY:+已设置}"
echo "PEXELS_API_KEY=${PEXELS_API_KEY:+已设置}"
```

### 4. 向用户展示配置状态

```
当前配置状态：

功能                  状态        说明
──────────────────────────────────────────────────────────
Manim 动画引擎        ✓/✗         ~/manim-env/bin/manim
TTS 配音 (Fish Audio) ✓/✗         需要 FISH_AUDIO_API_KEY（推荐，音质最高）
TTS 配音 (edge-tts)   ✓ 可用      免费备用，无需 Key
脚本生成 (AI)         ✓/✗         需要 ANTHROPIC_API_KEY（更高质量）
图片素材 (ffmpeg模式) ✓/✗         需要 PEXELS_API_KEY
当前 pipeline         manim       在 cut-config.yaml 中修改
当前 TTS provider     fish_audio  在 cut-config.yaml 中修改
```

### 5. 如果 Manim 未安装，引导安装

```bash
brew install python@3.12
python3.12 -m venv ~/manim-env
PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig" \
  ~/manim-env/bin/pip install manim "manim-voiceover[edge]" edge-tts fish-audio-sdk PyYAML
~/manim-env/bin/pip install "setuptools<71"
~/manim-env/bin/manim --version
```

### 6. 修改配置

直接编辑 `~/.claude/skills/cut/cut-config.yaml`（修改立即生效，因为是 symlink）：
- **切换 pipeline**：`pipeline: ffmpeg`
- **切换 TTS**：`tts.provider: edge_tts`（免费）或 `fish_audio`（推荐）
- **切换渲染质量**：`manim.quality: l`（低质量预览）

---

## 阶段二：执行流水线

配置确认后，读取 `cut-config.yaml` 中的 `pipeline` 字段选择流水线。

---

## Manim Pipeline（默认，`pipeline: manim`）

### Step 1：确认输入

询问用户：
1. 讲稿文件路径（Markdown 或纯文本）
2. 项目名称（默认取文件名）
3. 输出目录（默认 `~/AICODING/CREATION/cut/workspace`）

### Step 2：生成视听脚本

```bash
python3 ~/.claude/skills/cut/skills/draft-script/scripts/draft_script.py \
  --input <讲稿路径> \
  --project <项目名> \
  --workspace-base <输出目录>
```

完成后读取 `script_preview.md` 展示场景列表给用户。

脚本生成后，**由 AI 直接根据 script.json 为每个场景生成 Manim 动画代码**，不依赖外部 API。
每个场景的 `visual.type` 和 `visual.description` 是生成代码的主要依据：

- `handraw_chart` → 生成图表/时间轴/对比图等 Manim 动画
- `handraw_illustration` → 生成示意图/流程图等
- `video` / `image` → 生成文字动画 + 背景效果

### Step 3：生成 Manim 代码

先用脚本生成基础框架：

```bash
python3 ~/.claude/skills/cut/skills/manim-render/scripts/gen_manim_code.py \
  --script <script.json路径> \
  --output <workspace目录>/scenes.py \
  --config ~/.claude/skills/cut/cut-config.yaml
```

然后**读取 script.json 中每个场景的内容，直接改写 scenes.py**，为每个场景生成有意义的 Manim 动画：

- 时间轴场景 → `Line` + `Dot` + `Text` 动画
- 对比图场景 → 左右两栏 + `Arrow` 连接
- 层次图场景 → 叠加 `Rectangle` + 标注
- 数据图场景 → `BarChart` 或自定义条形图
- 文字场景 → `Write` + `FadeIn` 动画序列

Manim 代码规范：
1. 每个场景继承 `VoiceoverScene`
2. `with self.voiceover(text="...")` 包裹动画
3. 场景结尾 `FadeOut` 所有元素
4. 中文文字用 `Text(..., font="STHeiti")`
5. 数学公式用 `MathTex`

TTS provider 由 `cut-config.yaml` 的 `tts.provider` 控制，代码中对应：
- `fish_audio` → 在 `construct()` 顶部使用 `FishAudioService`
- `edge_tts` → 使用 `EdgeTTSService`

### Step 4：低画质预览第一个场景

```bash
~/manim-env/bin/manim -ql <workspace目录>/scenes.py <Scene01ClassName>
```

确认效果后继续。

### Step 5：批量渲染所有场景 + 合并

```bash
python3 ~/.claude/skills/cut/skills/manim-render/scripts/render_manim.py \
  --script <script.json路径> \
  --manim-file <workspace目录>/scenes.py \
  --output <workspace目录>/output/final.mp4 \
  --config ~/.claude/skills/cut/cut-config.yaml
```

完成后展示输出路径和视频时长。

---

## FFmpeg Pipeline（`pipeline: ffmpeg`）

### Step 1：确认输入（同上）

### Step 2：生成视听脚本（同上）

### Step 3：生成 TTS 旁白

```bash
python3 ~/.claude/skills/cut/skills/gen-assets/scripts/gen_tts.py \
  --script <script.json路径> \
  --workspace <workspace目录>
```

### Step 4：搜索素材（有 PEXELS_API_KEY 时执行）

```bash
python3 ~/.claude/skills/cut/skills/fetch-assets/scripts/fetch_assets.py \
  --script <script.json路径> \
  --workspace <workspace目录>
```

无 Key 时跳过，后续合成使用黑色填充帧。

### Step 5：生成手绘图 & AI 图片

```bash
# 手绘图（始终可用）
python3 ~/.claude/skills/cut/skills/gen-assets/scripts/gen_handraw.py \
  --script <script.json路径> --workspace <workspace目录>

# AI 图片（有 OPENAI_API_KEY 时执行）
python3 ~/.claude/skills/cut/skills/gen-assets/scripts/gen_image.py \
  --script <script.json路径> --workspace <workspace目录>
```

### Step 6：合成最终视频

```bash
python3 ~/.claude/skills/cut/skills/compose-video/scripts/compose.py \
  <script.json路径> \
  --output <workspace目录>/output/final.mp4 \
  --resolution 1280x720 \
  --fps 24 \
  --no-interactive
```

---

## 中断续跑

读取 `script.json` 的 `pipeline_state` 字段判断从哪步继续：

| 状态 | 含义 |
|------|------|
| `draft` | 脚本已生成 |
| `manim_code_generated` | Manim 代码已生成 |
| `manim_rendered` | 渲染完成 |
| `tts_done` | TTS 旁白完成（ffmpeg pipeline） |
| `composed` | 视频合成完成 |

---

## TTS 语音参考（edge-tts 备用时）

| 语音 | 特点 |
|------|------|
| `zh-CN-YunxiNeural` | 男声，知识讲解（默认） |
| `zh-CN-XiaoxiaoNeural` | 女声，温柔 |
| `zh-CN-YunyangNeural` | 男声，新闻播报 |
| `zh-CN-XiaoyiNeural` | 女声，活泼 |
