---
name: draft-script
description: Convert a text lecture/script (Markdown or TXT) into a structured audio-visual script (JSON format). Claude analyzes the lecture content, auto-splits into scenes, and generates narration, visual description, subtitles, and music mood for each scene.
trigger: Use when you need to convert a text lecture or article into a structured JSON script for video production.
version: "1.0"
---

# draft-script

Converts a plain-text lecture or Markdown document into a structured JSON audio-visual script following the cut schema. Uses Claude API to intelligently segment the content into scenes and generate all required metadata.

## Usage

```bash
python cut/skills/draft-script/scripts/draft_script.py \
  --input lecture.md \
  --project my_project \
  [--lang zh] \
  [--workspace-base ./workspace]
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--input` | Yes | — | Path to input lecture file (Markdown or TXT) |
| `--project` | Yes | — | Project name (used for workspace directory) |
| `--lang` | No | `zh` | Language of the lecture (`zh` or `en`) |
| `--workspace-base` | No | `./workspace` | Base directory for output workspace |

## Output

Outputs to `{workspace-base}/{project}/{timestamp}/`:
- `script.json` — Structured audio-visual script (validated against `script_schema.json`)
- `script_preview.md` — Human-readable Markdown table preview of all scenes

## Script JSON Format

```json
{
  "title": "Video Title",
  "total_duration": 300,
  "output_format": "mp4",
  "resolution": "1920x1080",
  "pipeline_state": "draft",
  "scenes": [
    {
      "id": "scene_01",
      "duration": 5,
      "narration": "Narration text",
      "subtitle": "Subtitle text (default same as narration)",
      "visual": {
        "type": "video|image|handraw_chart|handraw_illustration",
        "description": "Visual description for search/generation",
        "keywords": ["english", "keywords", "only"],
        "status": "pending",
        "selected_candidate": null,
        "candidates": [],
        "asset_path": null
      },
      "audio": {
        "narration_status": "pending",
        "narration_path": null,
        "music": {
          "description": "Background music mood description",
          "keywords": ["mood:calm", "genre:ambient"],
          "status": "pending",
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

## Notes

- `visual.keywords` are always in English (auto-translated by Claude) for Pexels/Pixabay search quality
- `visual.type` is chosen from: `video`, `image`, `handraw_chart`, `handraw_illustration`
- `pipeline_state` is always `"draft"` on initial generation
- Requires `ANTHROPIC_API_KEY` environment variable
