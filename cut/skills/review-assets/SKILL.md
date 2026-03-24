---
name: review-assets
description: Generate an interactive HTML review page for human approval of fetched/generated assets.
trigger: Use when you need to review and approve assets before video composition.
version: 1.0.0
---

# review-assets

Generates an interactive HTML page for human review and approval of video assets.

## Usage

```bash
python3 cut/skills/review-assets/scripts/generate_review.py <script_path> <output_html_path>
```

### Example

```bash
python3 cut/skills/review-assets/scripts/generate_review.py \
    workspace/my_project/20240101_120000/script.json \
    workspace/my_project/20240101_120000/review.html
```

Then open `review.html` in a browser to review assets.

## Workflow

1. Run `fetch-assets` (task4) or `gen-assets` (task5) to populate `script.json` with candidates.
2. Run `generate_review.py` to create `review.html`.
3. Open `review.html` in a browser.
4. For each scene:
   - Click a candidate to select it (sets `visual.status = "approved"`, `visual.selected_candidate = <index>`).
   - Or click **标记：需AI生成** to mark the scene for AI generation (`visual.status = "generating"`).
   - For background music candidates, do the same in the music section.
5. Click **保存审核结果** to save:
   - If served via a local HTTP server that supports `/save_script`, the file is written directly.
   - Otherwise, a `script.json` download is triggered — replace the original file with it.
6. After saving, `pipeline_state` is updated to `"assets_reviewed"`.

## Output

The generated HTML embeds the full `script.json` data and provides:

| Feature | Description |
|---------|-------------|
| Image preview | Thumbnail display with source attribution |
| Video preview | HTML5 `<video>` inline playback |
| Audio preview | HTML5 `<audio>` playback for music candidates |
| Single-select | Radio-style selection per scene |
| AI generation flag | Mark scenes for AI generation (sets `status = "generating"`) |
| State restoration | Pre-existing `selected_candidate` / `status` values are reflected on load |
| Save | Downloads updated `script.json` or POSTs to `/save_script` |

## script.json Fields Updated

| Field | Value |
|-------|-------|
| `scenes[i].visual.selected_candidate` | Index of selected candidate (int) |
| `scenes[i].visual.status` | `"approved"` or `"generating"` |
| `scenes[i].audio.music.selected_candidate` | Index of selected music candidate |
| `scenes[i].audio.music.status` | `"approved"` or `"generating"` |
| `pipeline_state` | `"assets_reviewed"` |

## Two Review Modes

- **Script review** (after task2): Review narration text and visual descriptions in `script.json`.
- **Asset review** (after task4/5): Review actual media files (images, videos, music) in the HTML page.
