# 技术规范 (Technical Specifications)

## 技术栈
- 语言: Python 3.11+（主要执行脚本）+ Markdown（SKILL.md 规范）
- 运行环境: 本地 macOS
- 视频处理: FFmpeg（系统依赖，运行前检测）
- 包管理: pip + requirements.txt（每个 skill 独立依赖）
- 配置管理: YAML（服务商配置、用户偏好）

## 架构设计

### 整体流水线
```
讲稿(文字) → [skill: draft-script] → 视听脚本(JSON)
                                          ↓
                              人工审核确认脚本
                                          ↓
                    ┌─────────────────────┼─────────────────────┐
              [skill: fetch-video]  [skill: fetch-image]  [skill: fetch-audio]
              [skill: gen-video]    [skill: gen-image]    [skill: gen-audio-tts]
              [skill: gen-handraw]
                    └─────────────────────┼─────────────────────┘
                                          ↓
                              人工审核素材（HTML交互页）
                                          ↓
                              [skill: compose-video]
                                          ↓
                              最终视频文件 (MP4/MOV等)
```

### 脚本格式规范（核心数据结构）
```json
{
  "title": "视频标题",
  "total_duration": 300,
  "output_format": "mp4",
  "resolution": "1920x1080",
  "pipeline_state": "draft|script_reviewed|assets_fetched|assets_reviewed|tts_done|composed",
  "scenes": [
    {
      "id": "scene_01",
      "duration": 5,
      "narration": "旁白文字内容",
      "subtitle": "字幕文字（默认同旁白）",
      "visual": {
        "type": "video|image|handraw_chart|handraw_illustration",
        "description": "画面描述（用于搜索/生成）",
        "keywords": ["english", "keywords", "only"],
        "status": "pending|candidates_ready|approved|generating|ready",
        "selected_candidate": null,
        "candidates": [],
        "asset_path": null
      },
      "audio": {
        "narration_status": "pending|ready",
        "narration_path": null,
        "music": {
          "description": "背景音乐氛围描述",
          "keywords": ["mood:calm", "genre:ambient"],
          "status": "pending|candidates_ready|approved|generating|ready",
          "selected_candidate": null,
          "candidates": [],
          "asset_path": null,
          "volume": 0.3
        }
      }
    }
  ]
}
```

### 依赖倒置规范（服务商抽象层）
每类 AI 服务必须定义统一接口，通过 `config.yaml` 切换实现：

```yaml
# cut-config.yaml
tts:
  provider: edge_tts  # edge_tts | openai | elevenlabs | azure
  voice: zh-CN-XiaoxiaoNeural

image_generation:
  provider: dalle3  # dalle3 | stable_diffusion | stability_ai

video_generation:
  provider: runway  # runway | kling_fal

stock_video:
  providers: [pexels, pixabay]  # 按顺序尝试

stock_image:
  providers: [pexels, pixabay]

music:
  providers: [jamendo, pixabay]  # 搜索优先
  fallback_generation: musicgen  # 本地 MusicGen 兜底
```

## Skills 目录结构规范
```
cut/
├── SKILL.md                    # 技能包总入口（符合 Anthropic 规范）
├── cut-config.yaml             # 服务商配置（用户可编辑）
├── skills/
│   ├── draft-script/
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   │   └── draft_script.py
│   │   └── references/
│   │       └── script_schema.json
│   ├── fetch-assets/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       ├── fetch_video.py
│   │       ├── fetch_image.py
│   │       └── fetch_music.py
│   ├── gen-assets/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       ├── providers/
│   │       │   ├── tts_base.py           # 抽象接口（Protocol）
│   │       │   ├── tts_edge.py
│   │       │   ├── tts_openai.py
│   │       │   ├── tts_elevenlabs.py
│   │       │   ├── image_base.py         # 抽象接口（Protocol）
│   │       │   ├── image_dalle3.py
│   │       │   ├── image_sdiffusion.py
│   │       │   ├── video_base.py         # 抽象接口（Protocol）
│   │       │   ├── video_runway.py
│   │       │   ├── handraw_base.py       # 抽象接口（Protocol）
│   │       │   ├── handraw_chart_svg.py  # 图表类：LLM → SVG → PNG（cairosvg）
│   │       │   └── handraw_illus_dalle.py # 插图类：DALL-E 3（手绘风格 prompt）
│   │       ├── gen_tts.py
│   │       ├── gen_image.py
│   │       ├── gen_video.py
│   │       └── gen_handraw.py            # 入口：按 visual.type 路由到对应 provider
│   ├── review-assets/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       ├── generate_review.py     # 生成 HTML 审核页
│   │       └── review.html            # 交互审核模板
│   └── compose-video/
│       ├── SKILL.md
│       └── scripts/
│           └── compose.py             # FFmpeg 合成
├── workspace/                         # 运行时工作目录
│   └── {project_name}/
│       └── {timestamp}/               # 每次运行独立目录，防止覆盖
│           ├── script.json
│           ├── assets/
│           │   ├── narration/
│           │   ├── video/
│           │   ├── image/
│           │   └── music/
│           └── output/
└── scripts/
    └── check_env.py                   # 环境检测脚本
```

## 开发规范
- 代码风格: PEP 8，函数式为主，避免复杂类继承
- 抽象接口: 每类服务用 Python Protocol 定义接口（而非 ABC）
- 错误处理: 每个外部 API 调用必须有明确的错误提示和降级策略
- 日志: 使用 Python logging，每个关键步骤输出进度
- 测试: 每个 skill 提供至少一个 smoke test（可用真实小样本运行）

## 工程实践
- 版本控制: Git，每个 skill 独立提交
- 环境检测: 运行任何 skill 前先调用 check_env.py
- 人工审核节点: 脚本生成后、素材搜索后各有一次人工确认
- 输出格式: 用户在 compose-video 阶段指定（mp4/mov/webm，分辨率）
