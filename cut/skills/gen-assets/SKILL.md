---
name: gen-assets
description: Generate TTS narration, AI images, AI video, and handraw visuals using configured AI providers.
trigger: Use when you need to generate AI assets for video production scenes.
version: "0.3"
---

# gen-assets

Generates AI assets for video production scenes, including TTS narration audio, images, video clips, and handraw visuals.

---

## TTS Narration (gen_tts.py)

Reads `script.json` and generates MP3 narration audio for each scene's `narration` field.

### Usage

```bash
python3 skills/gen-assets/scripts/gen_tts.py \
  --script workspace/{project}/script.json \
  --workspace workspace/{project} \
  [--provider edge_tts|openai|elevenlabs]
```

### Supported TTS Providers

| Provider | Cost | API Key | Notes |
|----------|------|---------|-------|
| `edge_tts` | Free | None | Microsoft Edge TTS, Chinese & English |
| `openai` | Paid | `OPENAI_API_KEY` | High quality, multilingual |
| `elevenlabs` | Paid | `ELEVENLABS_API_KEY` | Ultra-realistic voices |

### Provider Architecture

TTS providers follow the `TTSProvider` Protocol in `scripts/providers/tts_base.py`:

```python
class TTSProvider(Protocol):
    def synthesize(self, text: str, output_path: str, voice: str) -> None: ...
```

---

## Image Generation (gen_image.py)

Generates AI images for `image`-type scenes in `script.json`.

### Usage

```bash
# Process all image scenes in script.json
python3 skills/gen-assets/scripts/gen_image.py \
  --script workspace/{project}/script.json \
  --workspace workspace/{project} \
  [--provider dalle3|stable_diffusion]

# Single image generation
python3 skills/gen-assets/scripts/gen_image.py \
  --script dummy.json \
  --prompt "programmer at desk, cinematic lighting" \
  --output output.png
```

### Supported Image Providers

| Provider | Cost | API Key | Notes |
|----------|------|---------|-------|
| `dalle3` | Paid | `OPENAI_API_KEY` | DALL-E 3, ~$0.04/image (standard) |
| `stable_diffusion` | Paid | `STABILITY_API_KEY` | Stability AI, ~$0.002/image |

### Configuration (cut-config.yaml)

```yaml
image_generation:
  provider: dalle3            # dalle3 | stable_diffusion
  dalle3_model: dall-e-3
  dalle3_size: 1792x1024
  dalle3_quality: standard    # standard | hd
  stability_engine: stable-diffusion-xl-1024-v1-0
```

### Provider Architecture

Image providers follow the `ImageProvider` Protocol in `scripts/providers/image_base.py`:

```python
class ImageProvider(Protocol):
    def generate(self, prompt: str, output_path: str, size: str = '1792x1024', **kwargs) -> None: ...
```

To add a new provider, implement this interface and register in `gen_image.py`'s `_get_provider()`.

### Output

- Images saved to: `workspace/{project}/assets/images/scene_01_image.png`
- `script.json` updated: `visual.status` → `"ready"`, `visual.asset_path` → file path

---

## Video Generation (gen_video.py)

Generates AI video clips for `video`-type scenes in `script.json`.

### Usage

```bash
python3 skills/gen-assets/scripts/gen_video.py \
  --script workspace/{project}/script.json \
  --workspace workspace/{project} \
  [--provider runway] \
  [--duration 5]
```

### Supported Video Providers

| Provider | Cost | API Key | Notes |
|----------|------|---------|-------|
| `runway` | Paid | `RUNWAY_API_KEY` | Runway ML Gen-3 Alpha, ~$0.05/s |

### Configuration (cut-config.yaml)

```yaml
video_generation:
  provider: runway
  runway_model: gen3a_turbo
  runway_duration: 5          # seconds
```

### Provider Architecture

Video providers follow the `VideoProvider` Protocol in `scripts/providers/video_base.py`:

```python
class VideoProvider(Protocol):
    def generate(self, prompt: str, output_path: str, duration: int = 5, **kwargs) -> None: ...
```

`video_runway.py` uses async polling: submits job → polls status every 5s → downloads on SUCCEEDED.

### Output

- Videos saved to: `workspace/{project}/assets/videos/scene_01_video.mp4`
- `script.json` updated: `visual.status` → `"ready"`, `visual.asset_path` → file path

---

## Handraw Generation (gen_handraw.py)

Generates hand-drawn visuals for `handraw_chart` and `handraw_illustration` scene types.

### Usage

```bash
# Process all handraw scenes in script.json
python3 skills/gen-assets/scripts/gen_handraw.py \
  --script workspace/{project}/script.json \
  --workspace workspace/{project}

# Single handraw generation
python3 skills/gen-assets/scripts/gen_handraw.py \
  --script dummy.json \
  --subject "程序员数量逐年下降趋势折线图" \
  --output chart.png \
  --type handraw_chart
```

### Routing Strategy

| `visual.type` | Provider | Implementation |
|---------------|----------|----------------|
| `handraw_chart` | `HandrawChartSVGProvider` | LLM → SVG (rough style) → cairosvg → PNG |
| `handraw_illustration` | `HandrawIllusDalleProvider` | DALL-E 3 + hand-drawn style prompt |

### handraw_chart: LLM → SVG → PNG

- Uses Claude (preferred) or OpenAI GPT-4o-mini to generate rough-style SVG
- Falls back to a built-in SVG template if no API key is configured
- Converts SVG → PNG using `cairosvg` (pure Python, **no Node.js required**)
- Install: `pip install cairosvg`

### handraw_illustration: DALL-E 3 Hand-Drawn Style

- Appends fixed style suffix to prompt:
  `"hand-drawn illustration, sketch style, black ink on white, rough lines, pencil drawing, doodle art"`
- Uses `dall-e-3` model for best artistic quality
- Requires `OPENAI_API_KEY`

### Configuration (cut-config.yaml)

```yaml
handraw:
  chart_provider: svg                    # svg (cairosvg)
  chart_llm_model: gpt-4o
  chart_output_format: png
  chart_dpi: 150
  illustration_provider: dalle3
  illustration_style_prompt: "hand-drawn illustration style, sketch, black and white line art"
  illustration_size: 1792x1024
```

### Provider Architecture

Handraw providers follow the `HandrawProvider` Protocol in `scripts/providers/handraw_base.py`:

```python
class HandrawProvider(Protocol):
    def generate(self, subject: str, output_path: str, **kwargs) -> str: ...
```

**Adding a new provider** (no modification to `gen_handraw.py` needed):

1. Implement the `HandrawProvider` Protocol in a new file (e.g., `providers/handraw_mermaid.py`)
2. Register it in `gen_handraw.py`'s `provider_map` dict:
   ```python
   provider_map['handraw_mermaid'] = 'providers.handraw_mermaid:MermaidProvider'
   ```
3. Use `visual.type: handraw_mermaid` in your `script.json` scenes

### Output

- Images saved to: `workspace/{project}/assets/handraw/scene_01_handraw.png`
- `script.json` updated: `visual.status` → `"ready"`, `visual.asset_path` → file path

---

## API Key Setup

```bash
# OpenAI (DALL-E 3, GPT-4o-mini for charts)
export OPENAI_API_KEY=sk-...

# Stability AI (Stable Diffusion)
export STABILITY_API_KEY=sk-...

# Runway ML (video generation)
export RUNWAY_API_KEY=...

# Anthropic Claude (for chart SVG generation, optional)
export ANTHROPIC_API_KEY=sk-ant-...
```

## Cost Reference (approximate)

| Service | Cost |
|---------|------|
| DALL-E 3 standard 1792x1024 | ~$0.040/image |
| DALL-E 3 HD 1792x1024 | ~$0.080/image |
| Stability AI SDXL | ~$0.002/image |
| Runway Gen-3 Alpha Turbo | ~$0.05/second |
| OpenAI TTS | ~$0.015/1K chars |
| Edge TTS | Free |
| Claude Haiku (chart SVG) | ~$0.001/chart |
