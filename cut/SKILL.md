---
name: cut
version: "0.2.0"
description: 将文字讲稿转化为视频。当用户提到"把讲稿/文章做成视频"、"生成视频脚本"、"合成视频"、"视频制作流水线"、"cut 技能包"时使用。默认使用 Manim CE + manim-voiceover + edge-tts 生成动画讲解视频。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# cut — AI 视频生产技能包

## 你的任务

用户想把一篇文字讲稿制作成视频。**在执行任何流水线步骤之前，先完成环境检测和配置引导。**

默认使用 **Manim pipeline**（动画质量最高），可在 `cut-config.yaml` 中切换为 `ffmpeg` pipeline（传统素材拼接）。

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

重点关注 `pipeline` 字段（`manim` 或 `ffmpeg`）和 `tts.voice`。

### 3. 检测 Manim 环境

```bash
# 检查 manim venv
ls ~/manim-env/bin/manim 2>/dev/null && echo "✓ Manim 已安装" || echo "✗ Manim 未安装"
~/manim-env/bin/manim --version 2>/dev/null || true

# 检查 API Keys
echo "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:+已设置}"
echo "OPENAI_API_KEY=${OPENAI_API_KEY:+已设置}"
echo "PEXELS_API_KEY=${PEXELS_API_KEY:+已设置}"
```

### 4. 向用户展示配置状态

根据检测结果展示：

```
当前配置状态：

功能                  状态        说明
──────────────────────────────────────────────────────────
Manim 动画引擎        ✓/✗         ~/manim-env/bin/manim
TTS 配音 (edge-tts)   ✓ 可用      免费，无需 Key
脚本生成 (AI)         ✓/✗         需要 ANTHROPIC_API_KEY（更高质量）
图片素材 (ffmpeg模式) ✓/✗         需要 PEXELS_API_KEY
当前 pipeline         manim       在 cut-config.yaml 中修改
当前 TTS 语音         zh-CN-YunxiNeural（男声）
```

### 5. 如果 Manim 未安装，引导安装

```bash
# 安装 Python 3.12
brew install python@3.12

# 创建 venv
python3.12 -m venv ~/manim-env

# 安装 manim 套件
PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig" \
  ~/manim-env/bin/pip install manim "manim-voiceover[edge]" edge-tts
~/manim-env/bin/pip install "setuptools<71"

# 验证
~/manim-env/bin/manim --version
```

### 6. 如果用户想修改配置

直接编辑 `$SKILL_DIR/cut-config.yaml`：
- **切换 pipeline**：`pipeline: ffmpeg`
- **切换 TTS 语音**：`tts.voice: zh-CN-XiaoxiaoNeural`（女声）
- **切换渲染质量**：`manim.quality: l`（低质量预览）

**常用 edge-tts 中文语音：**
| 语音 | 特点 |
|------|------|
| `zh-CN-YunxiNeural` | 男声，知识讲解（默认） |
| `zh-CN-XiaoxiaoNeural` | 女声，温柔 |
| `zh-CN-YunyangNeural` | 男声，新闻播报风格 |
| `zh-CN-XiaoyiNeural` | 女声，活泼 |

---

## 阶段二：执行流水线

配置确认完成后，读取 `cut-config.yaml` 中的 `pipeline` 字段，选择对应流水线执行。

---

## Manim Pipeline（默认，`pipeline: manim`）

### Step 1：确认输入

询问用户：
1. 讲稿文件路径（Markdown 或纯文本）
2. 项目名称（默认取文件名）
3. 输出目录（默认 `./workspace`）

### Step 2：生成视听脚本

```bash
SKILL_DIR="$HOME/.claude/skills/cut"
python3 "$SKILL_DIR/skills/draft-script/scripts/draft_script.py" \
  --input <讲稿路径> \
  --project <项目名> \
  --workspace-base <输出目录>
```

完成后读取 `script_preview.md` 展示场景列表给用户。

**重要**：脚本生成后，**由 Claude 直接根据 script.json 为每个场景生成 Manim 动画代码**，不依赖外部 API。每个场景的 `visual.type` 和 `visual.description` 是生成代码的主要依据：

- `handraw_chart` → 生成图表/时间轴/对比图等 Manim 动画
- `handraw_illustration` → 生成示意图/流程图等
- `video` / `image` → 生成文字动画 + 背景效果

### Step 3：生成 Manim 代码

**Claude 直接生成 Manim 代码**，不调用任何外部 LLM API。

先用 `gen_manim_code.py` 生成基础框架：

```bash
SKILL_DIR="$HOME/.claude/skills/cut"
python3 "$SKILL_DIR/skills/manim-render/scripts/gen_manim_code.py" \
  --script <script.json路径> \
  --output <workspace目录>/scenes.py \
  --config "$SKILL_DIR/cut-config.yaml"
```

然后 **Claude 读取 script.json 中每个场景的内容，直接改写 scenes.py**，为每个场景生成真正有意义的 Manim 动画：

- 时间轴场景 → `Line` + `Dot` + `Text` 动画
- 对比图场景 → 左右两栏 + `Arrow` 连接
- 层次图场景 → 叠加 `Rectangle` + 标注
- 数据图场景 → `BarChart` 或自定义条形图
- 文字场景 → `Write` + `FadeIn` 动画序列

生成代码时遵循以下规范：
1. 每个场景继承 `VoiceoverScene`
2. `with self.voiceover(text="...")` 包裹动画
3. 场景结尾 `FadeOut` 所有元素
4. 中文文字用 `Text(..., font="STHeiti")`
5. 数学公式用 `MathTex`

### Step 4：TTS 旁白（manim-voiceover 自动处理）

manim-voiceover 在渲染时自动调用 edge-tts 生成配音，无需单独步骤。

TTS 语音由 `cut-config.yaml` 中的 `tts.voice` 控制。

### Step 5：渲染视频

```bash
SKILL_DIR="$HOME/.claude/skills/cut"

# 先低画质预览第一个场景
~/manim-env/bin/manim -ql <workspace目录>/scenes.py <Scene01ClassName>

# 确认效果后批量渲染所有场景
python3 "$SKILL_DIR/skills/manim-render/scripts/render_manim.py" \
  --script <script.json路径> \
  --manim-file <workspace目录>/scenes.py \
  --output <workspace目录>/output/final.mp4 \
  --config "$SKILL_DIR/cut-config.yaml"
```

完成后展示输出路径和视频时长。

---

## FFmpeg Pipeline（`pipeline: ffmpeg`）

### Step 1：确认输入（同上）

### Step 2：生成视听脚本（同上）

### Step 3：生成 TTS 旁白

```bash
SKILL_DIR="$HOME/.claude/skills/cut"
python3 "$SKILL_DIR/skills/gen-assets/scripts/gen_tts.py" \
  --script <script.json路径> \
  --workspace <workspace目录>
```

### Step 4：搜索素材（有 PEXELS/PIXABAY Key 时执行）

```bash
python3 "$SKILL_DIR/skills/fetch-assets/scripts/fetch_assets.py" \
  --script <script.json路径> \
  --workspace <workspace目录>
```

无 Key 时跳过，后续合成使用黑色填充帧。

### Step 5：生成 AI 素材

```bash
# 手绘图（始终可用）
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

### Step 7：合成最终视频

```bash
python3 "$SKILL_DIR/skills/compose-video/scripts/compose.py" \
  <script.json路径> \
  --output <workspace目录>/output/final.mp4 \
  --resolution 1280x720 \
  --fps 24 \
  --no-interactive
```

---

## 关键路径

- **skill 根目录**: `~/.claude/skills/cut/`（软链接到源码仓库）
- **配置文件**: `~/.claude/skills/cut/cut-config.yaml`
- **环境检测**: `scripts/check_env.py`
- **讲稿转脚本**: `skills/draft-script/scripts/draft_script.py`
- **Manim 代码生成框架**: `skills/manim-render/scripts/gen_manim_code.py`
- **Manim 批量渲染**: `skills/manim-render/scripts/render_manim.py`
- **TTS 旁白（ffmpeg模式）**: `skills/gen-assets/scripts/gen_tts.py`
- **素材搜索**: `skills/fetch-assets/scripts/fetch_assets.py`
- **手绘图**: `skills/gen-assets/scripts/gen_handraw.py`
- **AI 图片**: `skills/gen-assets/scripts/gen_image.py`
- **审核页面**: `skills/review-assets/scripts/generate_review.py`
- **视频合成（ffmpeg模式）**: `skills/compose-video/scripts/compose.py`

## pipeline_state 状态

| 状态 | 含义 |
|------|------|
| `draft` | 脚本已生成 |
| `manim_code_generated` | Manim 代码已生成（manim pipeline） |
| `manim_rendered` | Manim 渲染完成（manim pipeline） |
| `assets_fetched` | 素材搜索完成（ffmpeg pipeline） |
| `tts_done` | TTS 旁白完成（ffmpeg pipeline） |
| `assets_reviewed` | 素材审核完成（ffmpeg pipeline） |
| `composed` | 视频合成完成 |

如果用户想从中间某步继续，读取 `script.json` 的 `pipeline_state` 判断从哪里接着执行。
