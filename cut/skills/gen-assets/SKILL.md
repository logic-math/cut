---
name: gen-assets
description: Generate TTS narration, AI images, AI video, and handraw visuals using configured AI providers.
trigger: Use when you need to generate AI assets for video production scenes.
version: "0.2"
---

# gen-assets

Generates AI assets for video production scenes, including TTS narration audio, images, video clips, and handraw visuals.

## TTS Narration (gen-audio-tts)

Reads `script.json` and generates MP3 narration audio for each scene's `narration` field.

### Usage

```bash
python3 skills/gen-assets/scripts/gen_tts.py \
  --script workspace/{project}/script.json \
  --workspace workspace/{project} \
  [--provider edge_tts|openai|elevenlabs]
```

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--script` | Yes | Path to `script.json` |
| `--workspace` | Yes | Project workspace directory |
| `--provider` | No | TTS provider override (default: from `cut-config.yaml`) |

### Provider Configuration

Configure in `cut-config.yaml`:

```yaml
tts:
  provider: edge_tts        # edge_tts | openai | elevenlabs
  voice: zh-CN-XiaoxiaoNeural   # default voice for edge_tts
  openai_voice: alloy           # voice for openai provider
  elevenlabs_voice_id: ""       # voice ID for elevenlabs provider
```

### Supported Providers

| Provider | Cost | API Key Required | Notes |
|----------|------|-----------------|-------|
| `edge_tts` | Free | No | Microsoft Edge TTS, supports Chinese & English |
| `openai` | Paid | `OPENAI_API_KEY` | High quality, multilingual |
| `elevenlabs` | Paid | `ELEVENLABS_API_KEY` | Ultra-realistic voices |

### Output

- Audio files saved to: `workspace/{project}/assets/narration/scene_01.mp3`, etc.
- `script.json` updated: each scene's `audio.narration_path` field is filled with the absolute path.
- `audio.narration_status` set to `done` on success, `error` on failure.

### Example

```bash
# Generate narration with default edge_tts (free, no API key needed)
python3 skills/gen-assets/scripts/gen_tts.py \
  --script workspace/my_project/script.json \
  --workspace workspace/my_project

# Use OpenAI TTS (requires OPENAI_API_KEY)
export OPENAI_API_KEY=sk-...
python3 skills/gen-assets/scripts/gen_tts.py \
  --script workspace/my_project/script.json \
  --workspace workspace/my_project \
  --provider openai
```

### Voices

**edge_tts voices:**
- Chinese: `zh-CN-XiaoxiaoNeural` (female), `zh-CN-YunxiNeural` (male)
- English: `en-US-JennyNeural` (female), `en-US-GuyNeural` (male)

**OpenAI voices:** `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`

**ElevenLabs:** Use voice ID from your ElevenLabs account dashboard.

### Provider Architecture

TTS providers follow the `TTSProvider` Protocol defined in `scripts/providers/tts_base.py`:

```python
class TTSProvider(Protocol):
    def synthesize(self, text: str, output_path: str, voice: str) -> None: ...
```

To add a new provider, implement this interface in `scripts/providers/tts_{name}.py`.
