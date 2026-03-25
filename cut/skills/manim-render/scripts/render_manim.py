#!/usr/bin/env python3
"""render_manim.py — 批量渲染 Manim 场景并合并为最终 MP4。

Usage:
    python3 render_manim.py \
        --script path/to/script.json \
        --manim-file path/to/scenes.py \
        --output path/to/final.mp4 \
        --config path/to/cut-config.yaml \
        [--quality h]  # l/m/h/k
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def load_config(config_path: str) -> dict:
    try:
        import yaml
        with open(config_path) as f:
            return yaml.safe_load(f)
    except Exception:
        return {}


def get_manim_cli(config: dict) -> str:
    cli = config.get("manim", {}).get("cli", "~/manim-env/bin/manim")
    return os.path.expanduser(cli)


def get_quality(config: dict, override: str = "") -> str:
    if override:
        return override
    return config.get("manim", {}).get("quality", "h")


def render_scene(manim_cli: str, manim_file: str, class_name: str,
                 quality: str, media_dir: str) -> str | None:
    """Render a single Manim scene. Returns output video path or None on failure."""
    cmd = [
        manim_cli,
        f"-q{quality}",
        manim_file,
        class_name,
        "--media_dir", media_dir,
    ]
    print(f"  Rendering {class_name} ({quality} quality)...", end=" ", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"FAILED")
        print(f"    stderr: {result.stderr[-300:]}")
        return None

    # Find rendered file
    quality_map = {"l": "480p15", "m": "720p30", "h": "1080p60", "k": "2160p60"}
    quality_dir = quality_map.get(quality, "1080p60")
    manim_file_stem = Path(manim_file).stem
    video_path = Path(media_dir) / "videos" / manim_file_stem / quality_dir / f"{class_name}.mp4"

    if video_path.exists():
        print(f"OK ({video_path.stat().st_size // 1024}KB)")
        return str(video_path)
    else:
        # Try to find it
        for f in Path(media_dir).rglob(f"{class_name}.mp4"):
            print(f"OK (found at {f})")
            return str(f)
        print(f"FAILED (output not found)")
        return None


def concat_videos(video_paths: list[str], output_path: str) -> bool:
    """Concatenate multiple MP4 files using FFmpeg."""
    if not video_paths:
        print("Error: no video segments to concatenate")
        return False

    if len(video_paths) == 1:
        import shutil
        shutil.copy2(video_paths[0], output_path)
        return True

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for vp in video_paths:
            f.write(f"file '{vp}'\n")
        concat_list = f.name

    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list,
            "-c", "copy",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            print(f"FFmpeg concat failed: {result.stderr.decode()[-300:]}")
            return False
        return True
    finally:
        os.unlink(concat_list)


def main():
    parser = argparse.ArgumentParser(description="Render Manim scenes and merge")
    parser.add_argument("--script", required=True, help="Path to script.json")
    parser.add_argument("--manim-file", required=True, help="Path to generated .py file")
    parser.add_argument("--output", required=True, help="Output MP4 path")
    parser.add_argument("--config", default="", help="Path to cut-config.yaml")
    parser.add_argument("--quality", default="", help="Override quality: l/m/h/k")
    parser.add_argument("--scenes", nargs="*", help="Render only these scene class names")
    args = parser.parse_args()

    # Load config
    config = {}
    if args.config and os.path.exists(args.config):
        config = load_config(args.config)
    else:
        skill_dir = Path(__file__).parent.parent.parent.parent
        config_path = skill_dir / "cut-config.yaml"
        if config_path.exists():
            config = load_config(str(config_path))

    manim_cli = get_manim_cli(config)
    quality = get_quality(config, args.quality)

    if not os.path.exists(manim_cli):
        print(f"Error: Manim CLI not found at {manim_cli}")
        print("  Create venv: python3.12 -m venv ~/manim-env")
        print("  Install:     ~/manim-env/bin/pip install manim manim-voiceover edge-tts")
        sys.exit(1)

    # Load script to get scene list
    with open(args.script, encoding="utf-8") as f:
        script = json.load(f)

    scenes = script.get("scenes", [])
    if not scenes:
        print("Error: no scenes in script.json")
        sys.exit(1)

    # Build class names
    def class_name(scene_id: str) -> str:
        return "".join(p.capitalize() for p in scene_id.split("_"))

    all_class_names = [class_name(s.get("id", f"scene_{i:02d}")) for i, s in enumerate(scenes, 1)]
    target_classes = args.scenes if args.scenes else all_class_names

    # Media dir = same directory as manim file
    media_dir = str(Path(args.manim_file).parent / "media")

    print(f"Rendering {len(target_classes)} scenes (quality={quality})...")
    print(f"  Manim CLI: {manim_cli}")
    print(f"  Media dir: {media_dir}")
    print()

    rendered = []
    failed = []

    for cls in target_classes:
        video_path = render_scene(manim_cli, args.manim_file, cls, quality, media_dir)
        if video_path:
            rendered.append(video_path)
        else:
            failed.append(cls)

    print()
    print(f"Rendered: {len(rendered)}/{len(target_classes)} scenes")
    if failed:
        print(f"Failed:   {failed}")

    if not rendered:
        print("Error: no scenes rendered successfully")
        sys.exit(1)

    # Concatenate
    print(f"\nConcatenating {len(rendered)} segments → {args.output}")
    if concat_videos(rendered, args.output):
        size_mb = os.path.getsize(args.output) / 1024 / 1024
        print(f"Done: {args.output} ({size_mb:.1f} MB)")

        # Show duration
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", args.output],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            dur = float(result.stdout.strip())
            print(f"Duration: {int(dur//60)}m{int(dur%60)}s")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
