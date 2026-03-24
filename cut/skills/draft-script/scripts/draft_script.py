#!/usr/bin/env python3
"""draft_script.py — Convert text lecture to structured audio-visual script JSON."""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "references", "script_schema.json"
)

SYSTEM_PROMPT = """You are a professional video script writer. Convert the given lecture text into a structured audio-visual script.

Rules:
1. Split the content into 5-30 scenes depending on length (aim for ~30-60 seconds per scene).
2. For each scene generate:
   - narration: the exact text to be read aloud (Chinese or original language)
   - subtitle: same as narration by default
   - visual.type: choose from video|image|handraw_chart|handraw_illustration
     * Use handraw_chart for data, statistics, comparisons
     * Use handraw_illustration for abstract concepts, metaphors
     * Use video for dynamic action scenes
     * Use image for portraits, places, static scenes
   - visual.description: Chinese description of the desired visual
   - visual.keywords: 3-6 English keywords ONLY (translate from Chinese if needed) for stock search
   - audio.music.description: background music mood in Chinese
   - audio.music.keywords: English mood/genre tags like ["mood:melancholic", "genre:ambient"]
3. Duration estimation: ~150 characters per minute for Chinese narration (so ~2.5 chars/sec).
   Minimum scene duration: 3 seconds. Round to nearest integer.
4. visual.keywords MUST be English words only — no Chinese characters allowed.
5. Output valid JSON only, no markdown fences, no extra text.

Output format (JSON):
{
  "title": "<video title derived from content>",
  "total_duration": <sum of all scene durations>,
  "output_format": "mp4",
  "resolution": "1920x1080",
  "pipeline_state": "draft",
  "scenes": [
    {
      "id": "scene_01",
      "duration": <integer seconds>,
      "narration": "<narration text>",
      "subtitle": "<subtitle text>",
      "visual": {
        "type": "<video|image|handraw_chart|handraw_illustration>",
        "description": "<visual description>",
        "keywords": ["english", "keyword1", "keyword2"],
        "status": "pending",
        "selected_candidate": null,
        "candidates": [],
        "asset_path": null
      },
      "audio": {
        "narration_status": "pending",
        "narration_path": null,
        "music": {
          "description": "<music mood description>",
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
}"""


def estimate_duration(narration: str) -> int:
    """Estimate scene duration from narration length (~2.5 chars/sec for Chinese)."""
    chars = len(narration.strip())
    seconds = max(3, round(chars / 2.5))
    return seconds


def _split_into_scenes(text: str, min_scenes: int = 5, max_scenes: int = 30) -> list:
    """Split text into scene-sized chunks targeting min_scenes to max_scenes."""
    # First split into sentences
    sentences = re.split(r"(?<=[。！？.!?\n])", text)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]

    if not sentences:
        sentences = [text[i:i + 100] for i in range(0, len(text), 100) if text[i:i + 100].strip()]

    total_chars = sum(len(s) for s in sentences)
    # Target chars per scene: aim for middle of min/max range
    target_scenes = max(min_scenes, min(max_scenes, max(min_scenes, len(sentences))))
    target_chars_per_scene = max(50, total_chars // target_scenes)

    # Merge sentences into scene chunks
    chunks = []
    buf = ""
    for s in sentences:
        if buf and len(buf) >= target_chars_per_scene:
            chunks.append(buf)
            buf = s
        else:
            buf = (buf + s).strip() if buf else s
    if buf:
        chunks.append(buf)

    # Enforce min/max bounds
    if len(chunks) > max_scenes:
        # Merge adjacent chunks
        new_chunks = []
        merge_factor = len(chunks) // max_scenes + 1
        for i in range(0, len(chunks), merge_factor):
            new_chunks.append("".join(chunks[i:i + merge_factor]))
        chunks = new_chunks[:max_scenes]

    if len(chunks) < min_scenes and chunks:
        # Split the largest chunks
        while len(chunks) < min_scenes:
            # Find the longest chunk and split it in half
            longest_idx = max(range(len(chunks)), key=lambda i: len(chunks[i]))
            longest = chunks[longest_idx]
            if len(longest) < 20:
                break
            mid = len(longest) // 2
            # Try to split at a sentence boundary near the middle
            split_pos = mid
            for sep in ["。", "！", "？", ".", "!", "?"]:
                pos = longest.rfind(sep, 0, mid + 20)
                if pos > 0:
                    split_pos = pos + 1
                    break
            left = longest[:split_pos].strip()
            right = longest[split_pos:].strip()
            if left and right:
                chunks[longest_idx:longest_idx + 1] = [left, right]
            else:
                break

    return [c for c in chunks if c]


def _mock_script(lecture_text: str) -> dict:
    """Generate a deterministic mock script when no API key is available."""
    log.warning("No ANTHROPIC_API_KEY found — generating mock script for testing.")

    # Extract title from first heading
    title = "视频脚本"
    for line in lecture_text.splitlines():
        heading = re.match(r"^#+\s+(.+)", line.strip())
        if heading:
            title = heading.group(1)
            break

    # Remove code blocks and headings, keep narration text
    clean_lines = []
    in_code = False
    for line in lecture_text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if re.match(r"^#+\s+", line.strip()):
            continue
        clean_lines.append(line)
    clean_text = "\n".join(clean_lines).strip()

    if not clean_text:
        clean_text = lecture_text

    # Determine target scene count based on text length
    total_chars = len(clean_text)
    # ~150 chars per scene, but clamp to 5-30
    target = max(5, min(30, total_chars // 150))
    merged = _split_into_scenes(clean_text, min_scenes=target, max_scenes=30)

    if not merged:
        merged = [clean_text[:200]]

    visual_types = ["video", "image", "handraw_chart", "handraw_illustration"]
    music_moods = [
        ("沉思氛围", ["mood:melancholic", "genre:ambient"]),
        ("科技感", ["mood:futuristic", "genre:electronic"]),
        ("叙事感", ["mood:narrative", "genre:cinematic"]),
        ("平静", ["mood:calm", "genre:acoustic"]),
    ]

    # Simple English keyword mapping based on common Chinese terms
    keyword_map = {
        "程序员": ["programmer", "developer", "coding"],
        "代码": ["code", "programming", "software"],
        "AI": ["artificial intelligence", "AI", "machine learning"],
        "硅谷": ["silicon valley", "tech hub", "startup"],
        "数字": ["digital", "technology", "data"],
        "文明": ["civilization", "society", "humanity"],
        "进化": ["evolution", "progress", "transformation"],
        "消亡": ["decline", "extinction", "end"],
        "未来": ["future", "tomorrow", "innovation"],
        "人类": ["human", "people", "mankind"],
    }

    def extract_keywords(text: str) -> list:
        keywords = []
        for zh, en_list in keyword_map.items():
            if zh in text:
                keywords.extend(en_list[:2])
        if not keywords:
            keywords = ["technology", "modern", "concept"]
        return list(dict.fromkeys(keywords))[:5]  # deduplicate, max 5

    scenes = []
    total_duration = 0
    for i, para in enumerate(merged):
        scene_num = str(i + 1).zfill(2)
        duration = estimate_duration(para)
        total_duration += duration
        vtype = visual_types[i % len(visual_types)]
        mood_desc, mood_kw = music_moods[i % len(music_moods)]
        keywords = extract_keywords(para)

        scenes.append({
            "id": f"scene_{scene_num}",
            "duration": duration,
            "narration": para,
            "subtitle": para,
            "visual": {
                "type": vtype,
                "description": f"场景{scene_num}：{para[:40]}...",
                "keywords": keywords,
                "status": "pending",
                "selected_candidate": None,
                "candidates": [],
                "asset_path": None,
            },
            "audio": {
                "narration_status": "pending",
                "narration_path": None,
                "music": {
                    "description": mood_desc,
                    "keywords": mood_kw,
                    "status": "pending",
                    "selected_candidate": None,
                    "candidates": [],
                    "asset_path": None,
                    "volume": 0.3,
                },
            },
        })

    return {
        "title": title,
        "total_duration": total_duration,
        "output_format": "mp4",
        "resolution": "1920x1080",
        "pipeline_state": "draft",
        "scenes": scenes,
    }


def call_claude(lecture_text: str, api_key: str) -> dict:
    """Call Claude API to generate the script."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    log.info("Calling Claude API to generate script...")

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"请将以下讲稿转化为视听脚本：\n\n{lecture_text}",
            }
        ],
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        log.error(f"Claude returned invalid JSON: {e}")
        log.debug(f"Raw response: {raw[:500]}")
        raise


def validate_script(script: dict) -> None:
    """Validate script against JSON Schema."""
    schema_path = os.path.abspath(SCHEMA_PATH)
    if not os.path.exists(schema_path):
        log.warning(f"Schema file not found at {schema_path}, skipping validation.")
        return

    try:
        import jsonschema

        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        jsonschema.validate(instance=script, schema=schema)
        log.info("JSON Schema validation passed.")
    except ImportError:
        log.warning("jsonschema not installed, skipping validation.")
    except Exception as e:
        log.warning(f"Schema validation warning: {e}")


def generate_preview(script: dict) -> str:
    """Generate a human-readable Markdown table preview."""
    lines = [
        f"# {script.get('title', 'Script Preview')}",
        "",
        f"- **总时长**: {script.get('total_duration', 0)} 秒",
        f"- **场景数**: {len(script.get('scenes', []))}",
        f"- **状态**: {script.get('pipeline_state', 'draft')}",
        "",
        "| 场景编号 | 时长(s) | 旁白摘要 | 画面描述 | visual.type |",
        "|----------|---------|----------|----------|-------------|",
    ]

    for scene in script.get("scenes", []):
        sid = scene.get("id", "")
        duration = scene.get("duration", 0)
        narration = scene.get("narration", "")
        narration_short = narration[:40].replace("|", "｜") + ("..." if len(narration) > 40 else "")
        visual = scene.get("visual", {})
        desc = visual.get("description", "")
        desc_short = desc[:40].replace("|", "｜") + ("..." if len(desc) > 40 else "")
        vtype = visual.get("type", "")
        lines.append(f"| {sid} | {duration} | {narration_short} | {desc_short} | {vtype} |")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Convert lecture text to audio-visual script JSON")
    parser.add_argument("--input", required=True, help="Path to input lecture file")
    parser.add_argument("--project", required=True, help="Project name for workspace directory")
    parser.add_argument("--lang", default="zh", help="Language of the lecture (zh or en)")
    parser.add_argument("--workspace-base", default=None, help="Base directory for workspace output")
    args = parser.parse_args()

    # Read input file
    input_path = os.path.abspath(args.input)
    if not os.path.exists(input_path):
        log.error(f"Input file not found: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        lecture_text = f.read()

    log.info(f"Read {len(lecture_text)} chars from {input_path}")

    # Determine workspace base
    if args.workspace_base:
        workspace_base = os.path.abspath(args.workspace_base)
    else:
        # Default: workspace/ relative to cwd
        workspace_base = os.path.join(os.getcwd(), "workspace")

    # Create output directory: {workspace_base}/{project}/{timestamp}/
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(workspace_base, args.project, timestamp)
    os.makedirs(out_dir, exist_ok=True)
    log.info(f"Output directory: {out_dir}")

    # Generate script
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        script = call_claude(lecture_text, api_key)
        # Ensure pipeline_state is set
        script["pipeline_state"] = "draft"
    else:
        script = _mock_script(lecture_text)

    # Validate
    validate_script(script)

    # Write script.json
    script_json_path = os.path.join(out_dir, "script.json")
    with open(script_json_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    log.info(f"Wrote script.json to {script_json_path}")

    # Write script_preview.md
    preview_md = generate_preview(script)
    preview_path = os.path.join(out_dir, "script_preview.md")
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(preview_md)
    log.info(f"Wrote script_preview.md to {preview_path}")

    print(f"Done. Output: {out_dir}")
    print(f"  script.json:       {script_json_path}")
    print(f"  script_preview.md: {preview_path}")
    print(f"  Scenes: {len(script.get('scenes', []))}, Total duration: {script.get('total_duration', 0)}s")


if __name__ == "__main__":
    main()
