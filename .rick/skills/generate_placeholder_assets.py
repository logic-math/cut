# Description: 生成占位素材（PNG 图片 + MP4 视频）用于无 API Key 的流水线测试

import argparse
import json
import os
import struct
import subprocess
import sys
import zlib
from pathlib import Path


def generate_png(output_path: str, width: int = 640, height: int = 360,
                 color: tuple = (100, 150, 200)) -> str:
    """用纯 Python struct+zlib 生成 PNG 占位图，无需 PIL"""
    r, g, b = color
    raw_data = b""
    for _ in range(height):
        raw_data += b"\x00" + bytes([r, g, b] * width)

    def make_chunk(chunk_type, data):
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png += make_chunk(b"IHDR", ihdr_data)
    compressed = zlib.compress(raw_data)
    png += make_chunk(b"IDAT", compressed)
    png += make_chunk(b"IEND", b"")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_bytes(png)
    return output_path


def generate_video(output_path: str, duration: int = 10,
                   width: int = 1280, height: int = 720,
                   color: str = "blue") -> str:
    """用 FFmpeg lavfi color source 生成纯色占位视频"""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color={color}:size={width}x{height}:rate=25",
        "-t", str(duration),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr}")
    return output_path


def generate_for_script(script_path: str, duration: int = 10) -> dict:
    """为 script.json 中所有场景生成占位素材并更新 asset_path"""
    script_file = Path(script_path)
    script = json.loads(script_file.read_text())
    workspace = script_file.parent

    generated = []
    # 生成一个共用的占位视频
    video_placeholder = workspace / "assets" / "video" / "placeholder.mp4"
    if not video_placeholder.exists():
        generate_video(str(video_placeholder), duration=duration)
        generated.append(str(video_placeholder))

    for scene in script.get("scenes", []):
        visual = scene.get("visual", {})
        vtype = visual.get("type", "video")
        sid = scene.get("id", "scene_00")

        if visual.get("asset_path") and Path(visual["asset_path"]).exists():
            continue  # 已有素材，跳过

        if vtype == "video":
            visual["asset_path"] = str(video_placeholder)
            visual["status"] = "ready"
        elif vtype in ("image", "handraw_chart", "handraw_illustration"):
            colors = {"image": (100, 150, 200), "handraw_chart": (240, 240, 200), "handraw_illustration": (220, 200, 240)}
            color = colors.get(vtype, (128, 128, 128))
            png_path = workspace / "assets" / ("image" if vtype == "image" else "handraw") / f"{sid}.png"
            generate_png(str(png_path), color=color)
            visual["asset_path"] = str(png_path)
            visual["status"] = "ready"
            generated.append(str(png_path))

    script_file.write_text(json.dumps(script, ensure_ascii=False, indent=2))
    return {"pass": True, "generated": generated, "script": str(script_path)}


def run_test():
    """内置测试"""
    import tempfile
    import shutil

    tmpdir = Path(tempfile.mkdtemp())
    try:
        # 测试 PNG 生成
        png_path = str(tmpdir / "test.png")
        generate_png(png_path, width=64, height=64, color=(255, 0, 0))
        assert Path(png_path).exists() and Path(png_path).stat().st_size > 100, "PNG generation failed"

        # 测试 video 生成（需要 ffmpeg）
        try:
            mp4_path = str(tmpdir / "test.mp4")
            generate_video(mp4_path, duration=2, width=320, height=240)
            assert Path(mp4_path).exists() and Path(mp4_path).stat().st_size > 1000, "MP4 generation failed"
            video_ok = True
        except (RuntimeError, FileNotFoundError):
            video_ok = False

        print(json.dumps({"pass": True, "result": f"PNG ok, video={'ok' if video_ok else 'skipped (no ffmpeg)'}"}))
    finally:
        shutil.rmtree(tmpdir)


def main():
    parser = argparse.ArgumentParser(description="Generate placeholder assets for cut pipeline testing")
    parser.add_argument("--script", help="Path to script.json to fill with placeholder assets")
    parser.add_argument("--png", help="Generate a single PNG at this path")
    parser.add_argument("--video", help="Generate a single placeholder MP4 at this path")
    parser.add_argument("--duration", type=int, default=10, help="Duration for video (seconds)")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--color", default="blue", help="Color for video (FFmpeg color name)")
    parser.add_argument("--test", action="store_true", help="Run built-in tests")
    args = parser.parse_args()

    if args.test:
        run_test()
        return

    if args.png:
        path = generate_png(args.png, args.width, args.height)
        print(json.dumps({"pass": True, "result": path}))
    elif args.video:
        path = generate_video(args.video, args.duration, args.width, args.height, args.color)
        print(json.dumps({"pass": True, "result": path}))
    elif args.script:
        result = generate_for_script(args.script, args.duration)
        print(json.dumps(result, ensure_ascii=False))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
