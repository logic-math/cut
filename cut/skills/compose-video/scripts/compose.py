#!/usr/bin/env python3
"""compose.py — Compose final video from approved assets using FFmpeg.

Usage:
    python3 compose.py <script_path> --output <output_path> \
        [--resolution 1280x720] [--fps 24] [--format mp4] \
        [--music-volume 0.3] [--no-interactive]

Reads script.json (with asset_path filled in from review step), composes
all scenes into a final video using FFmpeg, and updates pipeline_state to
"composed".

Supported visual types:
    video   — direct use, with loop/trim alignment
    image   — Ken Burns zoom effect for scene duration
    handraw — fade-in animation for scene duration

Audio:
    narration (main track) + background music (volume-controlled)

Subtitles:
    Burned in via FFmpeg drawtext filter (one subtitle per scene).
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path


# ---------------------------------------------------------------------------
# Resolution presets
# ---------------------------------------------------------------------------
RESOLUTION_PRESETS = {
    '720p':  '1280x720',
    '1080p': '1920x1080',
    '4k':    '3840x2160',
    '4K':    '3840x2160',
}


def parse_resolution(res_str):
    """Return (width, height) tuple from '1280x720' or '720p' etc."""
    res_str = RESOLUTION_PRESETS.get(res_str, res_str)
    parts = res_str.lower().split('x')
    if len(parts) != 2:
        raise ValueError(f'Invalid resolution: {res_str}')
    return int(parts[0]), int(parts[1])


# ---------------------------------------------------------------------------
# FFprobe helpers
# ---------------------------------------------------------------------------
def ffprobe_duration(path):
    """Return duration in seconds (float) or None if unknown."""
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json',
         '-show_format', '-show_streams', path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
    except Exception:
        return None
    fmt = data.get('format', {})
    if 'duration' in fmt:
        return float(fmt['duration'])
    for stream in data.get('streams', []):
        if 'duration' in stream:
            return float(stream['duration'])
    return None


# ---------------------------------------------------------------------------
# SRT / subtitle generation
# ---------------------------------------------------------------------------
def seconds_to_srt_time(s):
    """Convert seconds (float) to SRT timestamp string HH:MM:SS,mmm."""
    ms = int(round((s % 1) * 1000))
    s = int(s)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    return f'{h:02d}:{m:02d}:{sec:02d},{ms:03d}'


def generate_srt(scenes, srt_path):
    """Write SRT subtitle file from scenes list."""
    lines = []
    t = 0.0
    for i, scene in enumerate(scenes, 1):
        dur = float(scene.get('duration', 5))
        subtitle = scene.get('subtitle', '').strip()
        if subtitle:
            start = seconds_to_srt_time(t)
            end = seconds_to_srt_time(t + dur - 0.1)
            lines.append(f'{i}')
            lines.append(f'{start} --> {end}')
            lines.append(subtitle)
            lines.append('')
        t += dur
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return srt_path


# ---------------------------------------------------------------------------
# Per-scene video segment building
# ---------------------------------------------------------------------------
def build_scene_segment(scene, width, height, fps, tmpdir, scene_idx):
    """
    Build a video-only segment (no audio) for a single scene.
    Returns path to the segment .mp4 file.
    """
    scene_dur = float(scene.get('duration', 5))
    visual = scene.get('visual', {})
    vtype = visual.get('type', 'image')
    asset_path = visual.get('asset_path') or ''

    out_path = os.path.join(tmpdir, f'seg_{scene_idx:03d}.mp4')

    if vtype == 'video' and asset_path and os.path.exists(asset_path):
        clip_dur = ffprobe_duration(asset_path)
        if clip_dur is None:
            clip_dur = scene_dur

        if clip_dur < scene_dur:
            # Loop: -stream_loop -1 with -t to cut to scene_dur
            cmd = [
                'ffmpeg', '-y',
                '-stream_loop', '-1',
                '-i', asset_path,
                '-t', str(scene_dur),
                '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,'
                       f'pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}',
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                '-an',
                out_path,
            ]
        else:
            # Trim middle: skip first 10%, take middle scene_dur seconds
            skip = clip_dur * 0.10
            # Ensure we don't seek past the end
            if skip + scene_dur > clip_dur:
                skip = max(0, clip_dur - scene_dur)
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(skip),
                '-i', asset_path,
                '-t', str(scene_dur),
                '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,'
                       f'pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}',
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                '-an',
                out_path,
            ]
    elif vtype in ('image', 'handraw') and asset_path and os.path.exists(asset_path):
        # Ken Burns zoom effect for image / fade-in for handraw
        if vtype == 'handraw':
            # Fade in: zoompan starts at z=1, slight pan
            vf = (
                f'scale={width*2}:{height*2},'
                f'zoompan=z=\'min(zoom+0.001,1.5)\':x=\'iw/2-(iw/zoom/2)\':y=\'ih/2-(ih/zoom/2)\':'
                f'd={int(fps * scene_dur)}:s={width}x{height}:fps={fps},'
                f'fade=t=in:st=0:d=0.5,'
                f'setsar=1'
            )
        else:
            # Ken Burns: slow zoom in
            vf = (
                f'scale={width*2}:{height*2},'
                f'zoompan=z=\'min(zoom+0.0015,1.5)\':x=\'iw/2-(iw/zoom/2)\':y=\'ih/2-(ih/zoom/2)\':'
                f'd={int(fps * scene_dur)}:s={width}x{height}:fps={fps},'
                f'setsar=1'
            )
        cmd = [
            'ffmpeg', '-y',
            '-loop', '1',
            '-i', asset_path,
            '-t', str(scene_dur),
            '-vf', vf,
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-an',
            out_path,
        ]
    else:
        # Fallback: black frame for scene_dur
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f'color=c=black:s={width}x{height}:r={fps}',
            '-t', str(scene_dur),
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-an',
            out_path,
        ]

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            f'FFmpeg failed building scene {scene_idx} segment:\n'
            + result.stderr.decode(errors='replace')[-500:]
        )
    return out_path


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------
def build_scene_audio(scene, scene_dur, tmpdir, scene_idx):
    """
    Mix narration + background music for a single scene.
    Returns path to mixed audio .aac file.
    """
    audio = scene.get('audio', {})
    narration_path = audio.get('narration_path', '')
    music_info = audio.get('music', {})
    music_path = music_info.get('asset_path', '')
    music_volume = float(music_info.get('volume', 0.3))

    out_path = os.path.join(tmpdir, f'audio_{scene_idx:03d}.aac')

    has_narration = narration_path and os.path.exists(narration_path)
    has_music = music_path and os.path.exists(music_path)

    if has_narration and has_music:
        # Mix narration (full vol) + music (attenuated) using amix/filter_complex
        filter_complex = (
            f'[0:a]atrim=0:{scene_dur},asetpts=PTS-STARTPTS,volume=1.0[narr];'
            f'[1:a]atrim=0:{scene_dur},asetpts=PTS-STARTPTS,volume={music_volume}[mus];'
            f'[narr][mus]amix=inputs=2:duration=longest[out]'
        )
        cmd = [
            'ffmpeg', '-y',
            '-i', narration_path,
            '-i', music_path,
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-t', str(scene_dur),
            '-c:a', 'aac', '-b:a', '128k',
            out_path,
        ]
    elif has_narration:
        cmd = [
            'ffmpeg', '-y',
            '-i', narration_path,
            '-t', str(scene_dur),
            '-c:a', 'aac', '-b:a', '128k',
            out_path,
        ]
    elif has_music:
        cmd = [
            'ffmpeg', '-y',
            '-i', music_path,
            '-t', str(scene_dur),
            '-af', f'volume={music_volume}',
            '-c:a', 'aac', '-b:a', '128k',
            out_path,
        ]
    else:
        # Silent audio
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f'anullsrc=r=44100:cl=stereo',
            '-t', str(scene_dur),
            '-c:a', 'aac', '-b:a', '128k',
            out_path,
        ]

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            f'FFmpeg failed building scene {scene_idx} audio:\n'
            + result.stderr.decode(errors='replace')[-500:]
        )
    return out_path


# ---------------------------------------------------------------------------
# Concatenation
# ---------------------------------------------------------------------------
def concat_segments(video_segments, audio_segments, output_path, width, height, fps, srt_path):
    """Concatenate all scene segments (video + audio) into final output."""
    assert len(video_segments) == len(audio_segments)
    n = len(video_segments)

    with tempfile.TemporaryDirectory() as concat_tmp:
        # Mux each video segment with its audio
        muxed = []
        for i, (vseg, aseg) in enumerate(zip(video_segments, audio_segments)):
            mux_path = os.path.join(concat_tmp, f'mux_{i:03d}.mp4')
            cmd = [
                'ffmpeg', '-y',
                '-i', vseg,
                '-i', aseg,
                '-c:v', 'copy', '-c:a', 'copy',
                '-shortest',
                mux_path,
            ]
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                raise RuntimeError(
                    f'FFmpeg mux failed for segment {i}:\n'
                    + result.stderr.decode(errors='replace')[-400:]
                )
            muxed.append(mux_path)

        # Write concat list file
        concat_list = os.path.join(concat_tmp, 'concat.txt')
        with open(concat_list, 'w') as f:
            for p in muxed:
                f.write(f"file '{p}'\n")

        # Concatenate all muxed segments
        raw_output = os.path.join(concat_tmp, 'raw_concat.mp4')
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat', '-safe', '0',
            '-i', concat_list,
            '-c:v', 'copy', '-c:a', 'copy',
            raw_output,
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(
                'FFmpeg concat failed:\n'
                + result.stderr.decode(errors='replace')[-500:]
            )

        # Burn subtitles if SRT exists and has content
        if srt_path and os.path.exists(srt_path) and os.path.getsize(srt_path) > 0:
            # Use drawtext via subtitles filter
            # Escape path for FFmpeg filter
            escaped_srt = srt_path.replace('\\', '/').replace(':', '\\:')
            cmd = [
                'ffmpeg', '-y',
                '-i', raw_output,
                '-vf', f"subtitles='{escaped_srt}'",
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                '-c:a', 'copy',
                output_path,
            ]
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                # subtitle burning failed (e.g. libass not available) — copy without subtitles
                print(
                    f'Warning: subtitle burning failed, outputting without subtitles. '
                    f'Error: {result.stderr.decode(errors="replace")[-200:]}',
                    file=sys.stderr
                )
                shutil.copy2(raw_output, output_path)
        else:
            shutil.copy2(raw_output, output_path)


# ---------------------------------------------------------------------------
# Main composition logic
# ---------------------------------------------------------------------------
def compose(script_path, output_path, width, height, fps, music_volume_default=0.3):
    """
    Main composition function.
    Reads script.json, builds per-scene segments, concatenates, burns subtitles.
    Updates pipeline_state to "composed" in script.json.
    """
    with open(script_path, 'r', encoding='utf-8') as f:
        script = json.load(f)

    scenes = script.get('scenes', [])
    if not scenes:
        raise ValueError('script.json has no scenes')

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Generate SRT subtitles
        srt_path = os.path.join(tmpdir, 'subtitles.srt')
        generate_srt(scenes, srt_path)

        video_segments = []
        audio_segments = []

        for i, scene in enumerate(scenes):
            scene_dur = float(scene.get('duration', 5))
            print(f'  Processing scene {i+1}/{len(scenes)}: {scene.get("id", "")} ({scene_dur}s)...',
                  file=sys.stderr)

            vseg = build_scene_segment(scene, width, height, fps, tmpdir, i)
            aseg = build_scene_audio(scene, scene_dur, tmpdir, i)
            video_segments.append(vseg)
            audio_segments.append(aseg)

        print(f'  Concatenating {len(scenes)} segments...', file=sys.stderr)
        concat_segments(video_segments, audio_segments, output_path, width, height, fps, srt_path)

    # Update pipeline_state in script.json
    script['pipeline_state'] = 'composed'
    with open(script_path, 'w', encoding='utf-8') as f:
        json.dump(script, f, ensure_ascii=False, indent=2)

    print(f'Composed: {output_path}', file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def ask_output_format():
    """Interactively ask user for output format parameters."""
    print('Output format configuration:')

    res_choices = {'1': '1280x720', '2': '1920x1080', '3': '3840x2160'}
    print('  Resolution: [1] 720p  [2] 1080p  [3] 4K  (default: 1)')
    choice = input('  Choice [1]: ').strip() or '1'
    resolution = res_choices.get(choice, '1280x720')

    fmt_choices = {'1': 'mp4', '2': 'mov'}
    print('  Format:     [1] mp4   [2] mov          (default: 1)')
    choice = input('  Choice [1]: ').strip() or '1'
    fmt = fmt_choices.get(choice, 'mp4')

    fps_choices = {'1': 24, '2': 30}
    print('  Frame rate: [1] 24fps [2] 30fps         (default: 1)')
    choice = input('  Choice [1]: ').strip() or '1'
    fps = fps_choices.get(choice, 24)

    return resolution, fmt, fps


def main():
    parser = argparse.ArgumentParser(
        description='Compose final video from script.json using FFmpeg.'
    )
    parser.add_argument('script', help='Path to script.json')
    parser.add_argument('--output', '-o', default=None,
                        help='Output file path (default: <script_dir>/output/final.mp4)')
    parser.add_argument('--resolution', default=None,
                        help='Output resolution: 720p / 1080p / 4K / WxH (default: ask)')
    parser.add_argument('--fps', type=int, default=None,
                        help='Output frame rate: 24 or 30 (default: ask)')
    parser.add_argument('--format', default=None, dest='fmt',
                        help='Output format: mp4 / mov (default: ask)')
    parser.add_argument('--music-volume', type=float, default=0.3,
                        help='Default background music volume 0.0-1.0 (default: 0.3)')
    parser.add_argument('--no-interactive', action='store_true',
                        help='Use defaults without asking (720p, mp4, 24fps)')
    args = parser.parse_args()

    script_path = os.path.abspath(args.script)
    if not os.path.exists(script_path):
        print(f'Error: script.json not found: {script_path}', file=sys.stderr)
        sys.exit(1)

    # Determine output format
    if args.no_interactive or (args.resolution and args.fps and args.fmt):
        resolution_str = args.resolution or '1280x720'
        fmt = args.fmt or 'mp4'
        fps = args.fps or 24
    else:
        resolution_str, fmt, fps = ask_output_format()
        if args.resolution:
            resolution_str = args.resolution
        if args.fps:
            fps = args.fps
        if args.fmt:
            fmt = args.fmt

    try:
        width, height = parse_resolution(resolution_str)
    except ValueError as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = os.path.abspath(args.output)
    else:
        script_dir = os.path.dirname(script_path)
        output_path = os.path.join(script_dir, 'output', f'final.{fmt}')

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print(f'Composing video: {width}x{height} @ {fps}fps -> {output_path}', file=sys.stderr)

    try:
        compose(script_path, output_path, width, height, fps, args.music_volume)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

    print(f'Done: {output_path}')
    sys.exit(0)


if __name__ == '__main__':
    main()
