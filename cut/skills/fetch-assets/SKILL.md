---
name: fetch-assets
description: Fetch stock video, image, and music asset candidates from Pexels, Pixabay, and Jamendo. Reads script.json keywords and populates candidates fields for human review.
trigger: Use when you need to search and populate stock asset candidates for video production scenes.
version: 1.0.0
---

# fetch-assets

Searches free stock asset libraries for video, image, and music candidates based on scene keywords in `script.json`. Results are written back to `script.json` for human review and selection.

## API Key Configuration

Three providers are supported. Set the corresponding environment variables before running:

| Provider | Environment Variable | Free Tier | Sign-up URL |
|----------|---------------------|-----------|-------------|
| Pexels   | `PEXELS_API_KEY`    | Yes (unlimited) | https://www.pexels.com/api/ |
| Pixabay  | `PIXABAY_API_KEY`   | Yes (unlimited) | https://pixabay.com/api/docs/ |
| Jamendo  | `JAMENDO_API_KEY`   | Yes (client_id) | https://developer.jamendo.com/v3.0 |

### Setting API Keys

```bash
export PEXELS_API_KEY=your_pexels_key_here
export PIXABAY_API_KEY=your_pixabay_key_here
export JAMENDO_API_KEY=your_jamendo_client_id_here
```

Or add them to your shell profile (`~/.zshrc`, `~/.bashrc`).

### Provider Priority

Configured in `cut-config.yaml`:

```yaml
stock_video:
  providers:
    - pexels    # tried first
    - pixabay   # fallback if pexels returns empty

stock_image:
  providers:
    - pexels
    - pixabay

music:
  providers:
    - jamendo   # tried first
    - pixabay   # fallback
```

## Usage

### Fetch all assets for a script

```bash
python3 cut/skills/fetch-assets/scripts/fetch_assets.py \
  --script workspace/my_project/20240101_120000/script.json
```

### Fetch only video candidates

```bash
python3 cut/skills/fetch-assets/scripts/fetch_video.py \
  --script workspace/my_project/20240101_120000/script.json
```

### Fetch only image candidates

```bash
python3 cut/skills/fetch-assets/scripts/fetch_image.py \
  --script workspace/my_project/20240101_120000/script.json
```

### Fetch only music candidates

```bash
python3 cut/skills/fetch-assets/scripts/fetch_music.py \
  --script workspace/my_project/20240101_120000/script.json
```

## Output Format

Each scene's `visual.candidates` (for video/image) and `audio.music.candidates` are populated with 3–5 items.

### Video/Image candidate fields

```json
{
  "url": "https://...",
  "duration": 15,
  "thumbnail": "https://...thumb.jpg",
  "provider": "pexels",
  "id": "12345",
  "width": 1920,
  "height": 1080,
  "license": "Pexels License (free for commercial use)",
  "source_url": "https://www.pexels.com/video/..."
}
```

### Music candidate fields

```json
{
  "name": "Calm Breeze",
  "artist": "John Doe",
  "duration": 180,
  "download_url": "https://mp3.jamendo.com/...",
  "provider": "jamendo",
  "id": "67890",
  "thumbnail": "https://...album.jpg",
  "license": "Creative Commons",
  "source_url": "https://www.jamendo.com/track/..."
}
```

## Music Keyword Format

Music keywords in `script.json` support mood and genre prefixes:

```json
"keywords": ["mood:calm", "genre:ambient"]
```

Supported prefixes:
- `mood:` — e.g. `calm`, `upbeat`, `dramatic`, `melancholic`, `energetic`
- `genre:` — e.g. `ambient`, `electronic`, `cinematic`, `jazz`, `classical`

Plain keywords (without prefix) are used as free-text search terms.

## Fallback Behavior

If the primary provider returns no results (e.g. API quota exceeded or network error), the skill automatically falls back to the next provider in the list. If all providers fail, an empty `candidates` list is returned and a warning is printed.

## Licenses

All supported providers offer free content for commercial use:
- **Pexels**: [Pexels License](https://www.pexels.com/license/)
- **Pixabay**: [Pixabay License](https://pixabay.com/service/license/)
- **Jamendo**: Creative Commons (varies per track, check `license` field)
