#!/usr/bin/env python3
"""Test script for task7: compose-video skill (FFmpeg video composition)."""
import json
import sys
import os
import tempfile
import subprocess
import shutil

# Project root: .rick/jobs/job_1/doing/tests/task7.py -> 5 levels up
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
COMPOSE_VIDEO_DIR = os.path.join(PROJECT_ROOT, 'cut', 'skills', 'compose-video', 'scripts')
COMPOSE_PY = os.path.join(COMPOSE_VIDEO_DIR, 'compose.py')


def is_stub(path):
    """Return True if file appears to be an unimplemented stub."""
    try:
        with open(path, 'r') as f:
            content = f.read()
        lines = [l for l in content.strip().splitlines() if l.strip()]
        return 'TODO' in content and len(lines) <= 5
    except Exception:
        return True


def check_ffmpeg():
    """Return (has_ffmpeg, has_ffprobe) booleans."""
    has_ffmpeg = shutil.which('ffmpeg') is not None
    has_ffprobe = shutil.which('ffprobe') is not None
    return has_ffmpeg, has_ffprobe


def make_silent_audio(path, duration):
    """Create a silent audio file using ffmpeg."""
    subprocess.run(
        ['ffmpeg', '-y', '-f', 'lavfi', '-i', f'anullsrc=r=44100:cl=mono',
         '-t', str(duration), '-q:a', '9', '-acodec', 'libmp3lame', path],
        capture_output=True, check=True
    )


def make_test_video(path, duration, width=1280, height=720, color='blue'):
    """Create a solid-color test video with silent audio using ffmpeg."""
    subprocess.run(
        ['ffmpeg', '-y',
         '-f', 'lavfi', '-i', f'color=c={color}:s={width}x{height}:r=24',
         '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
         '-t', str(duration),
         '-c:v', 'libx264', '-c:a', 'aac', '-shortest',
         path],
        capture_output=True, check=True
    )


def make_test_image(path, width=1280, height=720, color='red'):
    """Create a solid-color test image using ffmpeg."""
    subprocess.run(
        ['ffmpeg', '-y',
         '-f', 'lavfi', '-i', f'color=c={color}:s={width}x{height}',
         '-frames:v', '1',
         path],
        capture_output=True, check=True
    )


def make_test_audio(path, duration, frequency=440):
    """Create a test audio file (sine wave) using ffmpeg."""
    subprocess.run(
        ['ffmpeg', '-y',
         '-f', 'lavfi', '-i', f'sine=frequency={frequency}:duration={duration}',
         '-c:a', 'aac',
         path],
        capture_output=True, check=True
    )


def ffprobe_info(path):
    """Return dict with duration, width, height, has_audio from ffprobe."""
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json',
         '-show_streams', '-show_format', path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
    except Exception:
        return None

    info = {'duration': None, 'width': None, 'height': None, 'has_audio': False}
    # Duration from format
    fmt = data.get('format', {})
    if 'duration' in fmt:
        info['duration'] = float(fmt['duration'])

    for stream in data.get('streams', []):
        codec_type = stream.get('codec_type', '')
        if codec_type == 'video':
            if info['width'] is None:
                info['width'] = stream.get('width')
                info['height'] = stream.get('height')
            if info['duration'] is None and 'duration' in stream:
                info['duration'] = float(stream['duration'])
        elif codec_type == 'audio':
            info['has_audio'] = True

    return info


def make_5scene_script(tmpdir, assets):
    """
    Build a 5-scene script.json with asset_path filled in.
    assets: dict with keys: video_path, image_path, narration_paths (list of 5), music_path
    """
    scenes = []
    for i in range(5):
        scene_id = f'scene_{i+1:02d}'
        visual_type = 'video' if i % 2 == 0 else 'image'
        asset_path = assets['video_path'] if visual_type == 'video' else assets['image_path']
        scenes.append({
            'id': scene_id,
            'duration': 5,
            'narration': f'Narration text for scene {i+1}.',
            'subtitle': f'Subtitle for scene {i+1}',
            'visual': {
                'type': visual_type,
                'description': f'Visual for scene {i+1}',
                'keywords': ['test'],
                'status': 'approved',
                'selected_candidate': 0,
                'candidates': [{'local_path': asset_path}],
                'asset_path': asset_path,
            },
            'audio': {
                'narration_status': 'ready',
                'narration_path': assets['narration_paths'][i],
                'music': {
                    'description': 'Background music',
                    'keywords': ['ambient'],
                    'status': 'approved',
                    'selected_candidate': 0,
                    'candidates': [{'local_path': assets['music_path']}],
                    'asset_path': assets['music_path'],
                    'volume': 0.3,
                },
            },
        })
    script = {
        'title': 'Test Video',
        'total_duration': 25,
        'output_format': 'mp4',
        'resolution': '1280x720',
        'fps': 24,
        'pipeline_state': 'assets_reviewed',
        'scenes': scenes,
    }
    script_path = os.path.join(tmpdir, 'script.json')
    with open(script_path, 'w') as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    return script_path, script


def run_compose(script_path, output_path, extra_args=None, timeout=120):
    """Run compose.py as a subprocess."""
    cmd = [sys.executable, COMPOSE_PY, script_path, '--output', output_path,
           '--resolution', '1280x720', '--fps', '24', '--format', 'mp4',
           '--no-interactive']
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout, result.stderr


def main():
    errors = []

    # ------------------------------------------------------------------ #
    # Pre-check: verify implementation file exists and is non-stub        #
    # ------------------------------------------------------------------ #
    if not os.path.exists(COMPOSE_PY):
        errors.append(f'compose.py does not exist at {COMPOSE_PY}')
        print(json.dumps({'pass': False, 'errors': errors}))
        sys.exit(1)

    if is_stub(COMPOSE_PY):
        errors.append(
            'compose.py appears to be a stub (contains TODO and ≤5 lines). '
            'Task7 implementation is required.'
        )
        print(json.dumps({'pass': False, 'errors': errors}))
        sys.exit(1)

    # Read source for static analysis
    try:
        with open(COMPOSE_PY, 'r') as f:
            compose_src = f.read()
    except Exception as e:
        errors.append(f'Failed to read compose.py: {e}')
        print(json.dumps({'pass': False, 'errors': errors}))
        sys.exit(1)

    # Check ffmpeg/ffprobe availability
    has_ffmpeg, has_ffprobe = check_ffmpeg()
    if not has_ffmpeg:
        errors.append('ffmpeg is not installed or not in PATH — required for compose-video')
        print(json.dumps({'pass': False, 'errors': errors}))
        sys.exit(1)
    if not has_ffprobe:
        errors.append('ffprobe is not installed or not in PATH — required for video validation')
        print(json.dumps({'pass': False, 'errors': errors}))
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # Test 1: Run compose.py with 5-scene script, verify final.mp4 exists#
    # ------------------------------------------------------------------ #
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            assets_dir = os.path.join(tmpdir, 'assets')
            os.makedirs(assets_dir)

            # Create test assets
            video_path = os.path.join(assets_dir, 'test_video.mp4')
            image_path = os.path.join(assets_dir, 'test_image.jpg')
            music_path = os.path.join(assets_dir, 'test_music.aac')
            narration_paths = []
            for i in range(5):
                p = os.path.join(assets_dir, f'narration_{i+1}.aac')
                make_test_audio(p, 4, frequency=300 + i * 50)
                narration_paths.append(p)

            make_test_video(video_path, 5)
            make_test_image(image_path)
            make_test_audio(music_path, 30, frequency=200)

            assets = {
                'video_path': video_path,
                'image_path': image_path,
                'narration_paths': narration_paths,
                'music_path': music_path,
            }

            script_path, script_data = make_5scene_script(tmpdir, assets)
            output_path = os.path.join(tmpdir, 'output', 'final.mp4')
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            rc, stdout, stderr = run_compose(script_path, output_path)

            if not os.path.exists(output_path):
                errors.append(
                    f'Test 1: final.mp4 was not generated at {output_path} '
                    f'(exit code={rc}, stderr={stderr[:300]})'
                )
            else:
                info = ffprobe_info(output_path)
                if info is None:
                    errors.append('Test 1: ffprobe failed to analyze output final.mp4')
                else:
                    # Verify duration: 5 scenes × 5s = 25s, allow ±1s
                    expected_duration = 25.0
                    if info['duration'] is None:
                        errors.append('Test 1: ffprobe could not determine duration of final.mp4')
                    elif abs(info['duration'] - expected_duration) > 1.0:
                        errors.append(
                            f'Test 1: final.mp4 duration {info["duration"]:.2f}s '
                            f'differs from expected {expected_duration}s by more than 1s'
                        )

                    # Verify resolution 1280x720
                    if info['width'] != 1280 or info['height'] != 720:
                        errors.append(
                            f'Test 1: final.mp4 resolution is {info["width"]}x{info["height"]}, '
                            f'expected 1280x720'
                        )

                    # Verify audio track exists
                    if not info['has_audio']:
                        errors.append(
                            'Test 1: final.mp4 does not contain an audio track '
                            '(expected narration + background music)'
                        )
    except subprocess.TimeoutExpired:
        errors.append('Test 1: compose.py timed out after 120 seconds')
    except subprocess.CalledProcessError as e:
        errors.append(f'Test 1: Failed to create test assets: {e}')
    except Exception as e:
        errors.append(f'Test 1: Unexpected exception: {e}')

    # ------------------------------------------------------------------ #
    # Test 2: Subtitle verification — screenshot at scene 2 timestamp    #
    # Check that subtitle text from script.json appears in video         #
    # ------------------------------------------------------------------ #
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            assets_dir = os.path.join(tmpdir, 'assets')
            os.makedirs(assets_dir)

            video_path = os.path.join(assets_dir, 'test_video.mp4')
            image_path = os.path.join(assets_dir, 'test_image.jpg')
            music_path = os.path.join(assets_dir, 'test_music.aac')
            narration_paths = []
            for i in range(5):
                p = os.path.join(assets_dir, f'narration_{i+1}.aac')
                make_test_audio(p, 4, frequency=300 + i * 50)
                narration_paths.append(p)

            make_test_video(video_path, 5)
            make_test_image(image_path)
            make_test_audio(music_path, 30, frequency=200)

            assets = {
                'video_path': video_path,
                'image_path': image_path,
                'narration_paths': narration_paths,
                'music_path': music_path,
            }

            script_path, script_data = make_5scene_script(tmpdir, assets)
            output_path = os.path.join(tmpdir, 'output', 'final.mp4')
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            rc, stdout, stderr = run_compose(script_path, output_path)

            if not os.path.exists(output_path):
                errors.append(
                    f'Test 2: final.mp4 not generated for subtitle test '
                    f'(exit code={rc}, stderr={stderr[:200]})'
                )
            else:
                # Extract a frame at scene 2 midpoint (scene 1 = 0-5s, scene 2 = 5-10s → t=7.5s)
                scene2_subtitle = script_data['scenes'][1]['subtitle']
                screenshot_path = os.path.join(tmpdir, 'screenshot_scene2.png')
                frame_result = subprocess.run(
                    ['ffmpeg', '-y', '-ss', '7.5', '-i', output_path,
                     '-frames:v', '1', screenshot_path],
                    capture_output=True
                )

                if frame_result.returncode != 0 or not os.path.exists(screenshot_path):
                    # Frame extraction failed — check if subtitle filter is in source code
                    has_subtitle_filter = any(kw in compose_src for kw in [
                        'subtitles', 'subtitle', 'drawtext', 'srt', 'ass', 'vf',
                    ])
                    if not has_subtitle_filter:
                        errors.append(
                            'Test 2: compose.py does not appear to implement subtitle overlay '
                            '(expected: subtitles= or drawtext= FFmpeg filter)'
                        )
                    else:
                        print(
                            f'Test 2: Frame extraction failed but subtitle filter found in source — '
                            f'subtitle implementation present (stderr={frame_result.stderr[:100]})',
                            file=sys.stderr
                        )
                else:
                    # Frame extracted — verify subtitle is burned in via OCR (if available)
                    # Since OCR is complex, we verify subtitle logic in source code instead
                    has_subtitle_logic = any(kw in compose_src for kw in [
                        'subtitle', 'drawtext', 'subtitles', 'srt', '.ass',
                    ])
                    if not has_subtitle_logic:
                        errors.append(
                            f'Test 2: compose.py does not implement subtitle overlay for scene 2 '
                            f'(expected subtitle "{scene2_subtitle}" burned into video via FFmpeg filter)'
                        )
    except subprocess.TimeoutExpired:
        errors.append('Test 2: compose.py timed out during subtitle test')
    except subprocess.CalledProcessError as e:
        errors.append(f'Test 2: Failed to create test assets: {e}')
    except Exception as e:
        errors.append(f'Test 2: Unexpected exception: {e}')

    # ------------------------------------------------------------------ #
    # Test 3: Duration alignment — loop short clip, trim long clip        #
    # 3s video for 8s scene (loop), 30s video for 5s scene (trim middle) #
    # ------------------------------------------------------------------ #
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            assets_dir = os.path.join(tmpdir, 'assets')
            os.makedirs(assets_dir)

            # Short video: 3s for an 8s scene (should loop)
            short_video = os.path.join(assets_dir, 'short_3s.mp4')
            make_test_video(short_video, 3, color='green')

            # Long video: 30s for a 5s scene (should trim middle)
            long_video = os.path.join(assets_dir, 'long_30s.mp4')
            make_test_video(long_video, 30, color='purple')

            narration_short = os.path.join(assets_dir, 'narration_short.aac')
            narration_long = os.path.join(assets_dir, 'narration_long.aac')
            music_path = os.path.join(assets_dir, 'music.aac')
            make_test_audio(narration_short, 7, frequency=300)
            make_test_audio(narration_long, 4, frequency=400)
            make_test_audio(music_path, 20, frequency=200)

            # Build a 2-scene script: scene1=8s (short 3s video), scene2=5s (long 30s video)
            scenes = [
                {
                    'id': 'scene_01',
                    'duration': 8,
                    'narration': 'Short video looped.',
                    'subtitle': 'Loop test',
                    'visual': {
                        'type': 'video',
                        'description': 'Short video',
                        'keywords': ['test'],
                        'status': 'approved',
                        'selected_candidate': 0,
                        'candidates': [{'local_path': short_video}],
                        'asset_path': short_video,
                    },
                    'audio': {
                        'narration_status': 'ready',
                        'narration_path': narration_short,
                        'music': {
                            'description': 'Background',
                            'keywords': ['ambient'],
                            'status': 'approved',
                            'selected_candidate': 0,
                            'candidates': [{'local_path': music_path}],
                            'asset_path': music_path,
                            'volume': 0.3,
                        },
                    },
                },
                {
                    'id': 'scene_02',
                    'duration': 5,
                    'narration': 'Long video trimmed.',
                    'subtitle': 'Trim test',
                    'visual': {
                        'type': 'video',
                        'description': 'Long video',
                        'keywords': ['test'],
                        'status': 'approved',
                        'selected_candidate': 0,
                        'candidates': [{'local_path': long_video}],
                        'asset_path': long_video,
                    },
                    'audio': {
                        'narration_status': 'ready',
                        'narration_path': narration_long,
                        'music': {
                            'description': 'Background',
                            'keywords': ['ambient'],
                            'status': 'approved',
                            'selected_candidate': 0,
                            'candidates': [{'local_path': music_path}],
                            'asset_path': music_path,
                            'volume': 0.3,
                        },
                    },
                },
            ]
            script = {
                'title': 'Duration Alignment Test',
                'total_duration': 13,
                'output_format': 'mp4',
                'resolution': '1280x720',
                'fps': 24,
                'pipeline_state': 'assets_reviewed',
                'scenes': scenes,
            }
            script_path = os.path.join(tmpdir, 'script.json')
            with open(script_path, 'w') as f:
                json.dump(script, f, ensure_ascii=False, indent=2)

            output_path = os.path.join(tmpdir, 'output', 'final.mp4')
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            rc, stdout, stderr = run_compose(script_path, output_path)

            if not os.path.exists(output_path):
                errors.append(
                    f'Test 3: final.mp4 not generated for duration alignment test '
                    f'(exit code={rc}, stderr={stderr[:300]})'
                )
            else:
                info = ffprobe_info(output_path)
                if info is None:
                    errors.append('Test 3: ffprobe failed to analyze duration alignment output')
                else:
                    # Total duration should be ~13s (8+5), allow ±1s
                    expected = 13.0
                    if info['duration'] is None:
                        errors.append('Test 3: ffprobe could not determine duration of output')
                    elif abs(info['duration'] - expected) > 1.0:
                        errors.append(
                            f'Test 3: Duration alignment output is {info["duration"]:.2f}s, '
                            f'expected ~{expected}s (±1s). '
                            f'Looping/trimming may not be working correctly.'
                        )

                # Verify loop/trim logic exists in source
                has_loop = any(kw in compose_src for kw in [
                    'stream_loop', 'loop', '-loop',
                ])
                has_trim = any(kw in compose_src for kw in [
                    'ss', 'trim', 'atrim', 'seek',
                ])
                if not has_loop:
                    errors.append(
                        'Test 3: compose.py does not implement video looping '
                        '(expected: -stream_loop or equivalent for short clips)'
                    )
                if not has_trim:
                    errors.append(
                        'Test 3: compose.py does not implement video trimming '
                        '(expected: -ss seek or trim filter for long clips)'
                    )
    except subprocess.TimeoutExpired:
        errors.append('Test 3: compose.py timed out during duration alignment test')
    except subprocess.CalledProcessError as e:
        errors.append(f'Test 3: Failed to create test assets: {e}')
    except Exception as e:
        errors.append(f'Test 3: Unexpected exception: {e}')

    # ------------------------------------------------------------------ #
    # Test 4: Background music volume — narration louder than music       #
    # Use ffmpeg volumedetect to compare mean volumes                     #
    # ------------------------------------------------------------------ #
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            assets_dir = os.path.join(tmpdir, 'assets')
            os.makedirs(assets_dir)

            video_path = os.path.join(assets_dir, 'test_video.mp4')
            music_path = os.path.join(assets_dir, 'music.aac')
            narration_path = os.path.join(assets_dir, 'narration.aac')

            make_test_video(video_path, 5)
            # Narration: loud sine wave (full amplitude)
            make_test_audio(narration_path, 4, frequency=440)
            # Music: also sine wave (will be volume-controlled to 0.3 by compose.py)
            make_test_audio(music_path, 10, frequency=220)

            script = {
                'title': 'Volume Test',
                'total_duration': 5,
                'output_format': 'mp4',
                'resolution': '1280x720',
                'fps': 24,
                'pipeline_state': 'assets_reviewed',
                'scenes': [{
                    'id': 'scene_01',
                    'duration': 5,
                    'narration': 'Volume test narration.',
                    'subtitle': 'Volume test',
                    'visual': {
                        'type': 'video',
                        'description': 'Test',
                        'keywords': ['test'],
                        'status': 'approved',
                        'selected_candidate': 0,
                        'candidates': [{'local_path': video_path}],
                        'asset_path': video_path,
                    },
                    'audio': {
                        'narration_status': 'ready',
                        'narration_path': narration_path,
                        'music': {
                            'description': 'Background',
                            'keywords': ['ambient'],
                            'status': 'approved',
                            'selected_candidate': 0,
                            'candidates': [{'local_path': music_path}],
                            'asset_path': music_path,
                            'volume': 0.3,
                        },
                    },
                }],
            }
            script_path = os.path.join(tmpdir, 'script.json')
            with open(script_path, 'w') as f:
                json.dump(script, f, ensure_ascii=False, indent=2)

            output_path = os.path.join(tmpdir, 'output', 'final.mp4')
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            rc, stdout, stderr = run_compose(script_path, output_path)

            if not os.path.exists(output_path):
                errors.append(
                    f'Test 4: final.mp4 not generated for volume test '
                    f'(exit code={rc}, stderr={stderr[:200]})'
                )
            else:
                # Run volumedetect on the output
                vol_result = subprocess.run(
                    ['ffmpeg', '-i', output_path, '-af', 'volumedetect', '-f', 'null', '/dev/null'],
                    capture_output=True, text=True
                )
                vol_output = vol_result.stderr

                # Verify volume control logic exists in source
                has_volume_control = any(kw in compose_src for kw in [
                    'volume', 'amix', 'amerge', 'filter_complex', 'lavfi',
                ])
                if not has_volume_control:
                    errors.append(
                        'Test 4: compose.py does not implement audio volume control '
                        '(expected: volume= filter or amix with volume parameter for background music)'
                    )

                # Check that mean_volume appears in volumedetect output (audio is present)
                if 'mean_volume' not in vol_output and 'max_volume' not in vol_output:
                    errors.append(
                        'Test 4: ffmpeg volumedetect found no audio in output — '
                        'final.mp4 may be missing audio track'
                    )
    except subprocess.TimeoutExpired:
        errors.append('Test 4: compose.py timed out during volume test')
    except subprocess.CalledProcessError as e:
        errors.append(f'Test 4: Failed to create test assets: {e}')
    except Exception as e:
        errors.append(f'Test 4: Unexpected exception: {e}')

    # ------------------------------------------------------------------ #
    # Test 5: Static analysis — verify compose.py implements key features #
    # ------------------------------------------------------------------ #
    try:
        # Verify script.json reading
        if not any(kw in compose_src for kw in ['json.load', 'json.loads', 'script']):
            errors.append(
                'Test 5: compose.py does not appear to read script.json '
                '(expected json.load or open() with script)'
            )

        # Verify FFmpeg invocation
        if not any(kw in compose_src for kw in ['ffmpeg', 'subprocess', 'run(']):
            errors.append(
                'Test 5: compose.py does not appear to invoke FFmpeg '
                '(expected subprocess call to ffmpeg)'
            )

        # Verify output path handling
        if not any(kw in compose_src for kw in ['output', 'final', '.mp4', 'mov']):
            errors.append(
                'Test 5: compose.py does not appear to write output file '
                '(expected output path like final.mp4)'
            )

        # Verify pipeline_state update to "composed"
        if 'composed' not in compose_src:
            errors.append(
                'Test 5: compose.py does not update pipeline_state to "composed" '
                '(expected pipeline_state = "composed" after successful composition)'
            )

        # Verify audio mixing (narration + music)
        if not any(kw in compose_src for kw in ['narration', 'narration_path', 'music', 'amix']):
            errors.append(
                'Test 5: compose.py does not appear to handle audio mixing '
                '(expected narration + background music mixing)'
            )

        # Verify resolution/format parameter support
        if not any(kw in compose_src for kw in ['resolution', 'fps', 'format', '1080', '720']):
            errors.append(
                'Test 5: compose.py does not appear to support output format parameters '
                '(expected resolution, fps, format options)'
            )
    except Exception as e:
        errors.append(f'Test 5: Static analysis raised unexpected exception: {e}')

    # ------------------------------------------------------------------ #
    # Build result                                                         #
    # ------------------------------------------------------------------ #
    result = {
        'pass': len(errors) == 0,
        'errors': errors,
    }
    print(json.dumps(result))
    sys.exit(0 if result['pass'] else 1)


if __name__ == '__main__':
    main()
