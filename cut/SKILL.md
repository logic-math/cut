---
name: cut
description: Context-First AI Coding Framework for producing video content from scripts. Orchestrates a pipeline from draft script through asset fetching/generation, human review, and final video composition.
trigger: Use this skill when you need to create a video from a text script, manage the video production pipeline, or work with any of the cut sub-skills (draft-script, fetch-assets, gen-assets, review-assets, compose-video).
version: "0.1.0"
---

# cut — AI Video Production Skill Pack

`cut` is a modular skill pack for producing video content using AI services. It takes a text script and produces a final composed video through a structured pipeline with human review checkpoints.

## Pipeline Overview

```
讲稿(文字) → [draft-script] → 视听脚本(JSON)
                                    ↓
                        人工审核确认脚本
                                    ↓
          [fetch-assets] / [gen-assets] (并行)
                                    ↓
                        人工审核素材（HTML交互页）
                                    ↓
                        [compose-video]
                                    ↓
                        最终视频文件 (MP4/MOV等)
```

## Sub-Skills

| Skill | Description |
|-------|-------------|
| `draft-script` | Convert a text lecture into a structured audio-visual script (JSON) |
| `fetch-assets` | Fetch stock video, image, and music assets |
| `gen-assets` | Generate TTS narration, AI images, AI video, and handraw visuals |
| `review-assets` | Generate an interactive HTML review page for human asset approval |
| `compose-video` | Compose all approved assets into a final video using FFmpeg |

## Configuration

Edit `cut-config.yaml` to configure AI service providers (TTS, image generation, video generation, etc.).

## Environment Setup

Before running any skill, check your environment:

```bash
python cut/scripts/check_env.py
```

## Workspace

Each run creates an isolated workspace directory:

```
workspace/{project_name}/{timestamp}/
├── script.json
├── assets/
│   ├── narration/
│   ├── video/
│   ├── image/
│   └── music/
└── output/
```
