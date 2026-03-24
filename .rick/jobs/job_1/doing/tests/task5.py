#!/usr/bin/env python3
"""Test script for task5: gen-assets skill (AI image/video/handraw generation)."""
import json
import sys
import os
import importlib.util
import tempfile
import subprocess

# Project root: .rick/jobs/job_1/doing/tests/task5.py -> 5 levels up
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
GEN_ASSETS_DIR = os.path.join(PROJECT_ROOT, 'cut', 'skills', 'gen-assets', 'scripts')
PROVIDERS_DIR = os.path.join(GEN_ASSETS_DIR, 'providers')

GEN_IMAGE_PY = os.path.join(GEN_ASSETS_DIR, 'gen_image.py')
GEN_VIDEO_PY = os.path.join(GEN_ASSETS_DIR, 'gen_video.py')
GEN_HANDRAW_PY = os.path.join(GEN_ASSETS_DIR, 'gen_handraw.py')
IMAGE_BASE_PY = os.path.join(PROVIDERS_DIR, 'image_base.py')
IMAGE_DALLE3_PY = os.path.join(PROVIDERS_DIR, 'image_dalle3.py')
IMAGE_SDIFF_PY = os.path.join(PROVIDERS_DIR, 'image_sdiffusion.py')
VIDEO_BASE_PY = os.path.join(PROVIDERS_DIR, 'video_base.py')
VIDEO_RUNWAY_PY = os.path.join(PROVIDERS_DIR, 'video_runway.py')
HANDRAW_BASE_PY = os.path.join(PROVIDERS_DIR, 'handraw_base.py')
HANDRAW_CHART_PY = os.path.join(PROVIDERS_DIR, 'handraw_chart_svg.py')
HANDRAW_ILLUS_PY = os.path.join(PROVIDERS_DIR, 'handraw_illus_dalle.py')


def load_module(path, name):
    """Load a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def is_stub(path):
    """Return True if file appears to be an unimplemented stub."""
    try:
        with open(path, 'r') as f:
            content = f.read()
        lines = [l for l in content.strip().splitlines() if l.strip()]
        return 'TODO' in content and len(lines) <= 5
    except Exception:
        return True


def is_valid_png(path):
    """Check if file exists and has a valid PNG header."""
    if not os.path.exists(path):
        return False, 'file does not exist'
    if os.path.getsize(path) < 8:
        return False, 'file too small to be a valid PNG'
    try:
        with open(path, 'rb') as f:
            header = f.read(8)
        if header[:8] == b'\x89PNG\r\n\x1a\n':
            return True, ''
        # Also accept JPEG
        if header[:2] == b'\xff\xd8':
            return True, ''
        return False, f'invalid image header: {header[:8].hex()}'
    except Exception as e:
        return False, str(e)


def make_script_with_scene(visual_type='image', description='test scene'):
    """Create a minimal script.json dict with one scene."""
    return {
        'title': 'Test Script',
        'total_duration': 10,
        'output_format': 'mp4',
        'resolution': '1920x1080',
        'pipeline_state': 'draft',
        'scenes': [{
            'id': 'scene_01',
            'duration': 5,
            'narration': 'Test narration.',
            'subtitle': 'Test subtitle.',
            'visual': {
                'type': visual_type,
                'description': description,
                'keywords': ['test'],
                'status': 'pending',
                'selected_candidate': None,
                'candidates': [],
                'asset_path': None,
            },
            'audio': {
                'narration_status': 'pending',
                'narration_path': None,
                'music': {
                    'description': 'test music',
                    'keywords': ['ambient'],
                    'status': 'pending',
                    'selected_candidate': None,
                    'candidates': [],
                    'asset_path': None,
                    'volume': 0.3,
                },
            },
        }],
    }


def main():
    errors = []

    # ------------------------------------------------------------------ #
    # Pre-check: verify all implementation files exist and are non-stubs  #
    # ------------------------------------------------------------------ #
    required_files = [
        (GEN_IMAGE_PY, 'gen_image.py'),
        (GEN_VIDEO_PY, 'gen_video.py'),
        (GEN_HANDRAW_PY, 'gen_handraw.py'),
        (IMAGE_BASE_PY, 'providers/image_base.py'),
        (IMAGE_DALLE3_PY, 'providers/image_dalle3.py'),
        (IMAGE_SDIFF_PY, 'providers/image_sdiffusion.py'),
        (VIDEO_BASE_PY, 'providers/video_base.py'),
        (VIDEO_RUNWAY_PY, 'providers/video_runway.py'),
        (HANDRAW_BASE_PY, 'providers/handraw_base.py'),
        (HANDRAW_CHART_PY, 'providers/handraw_chart_svg.py'),
        (HANDRAW_ILLUS_PY, 'providers/handraw_illus_dalle.py'),
    ]
    for path, label in required_files:
        if not os.path.exists(path):
            errors.append(f'{label} does not exist at {path}')
        elif is_stub(path):
            errors.append(
                f'{label} appears to be a stub (contains TODO and ≤5 lines). '
                'Task5 implementation is required.'
            )

    if errors:
        result = {'pass': False, 'errors': errors}
        print(json.dumps(result))
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # Load modules                                                         #
    # ------------------------------------------------------------------ #
    gen_image_mod = None
    gen_video_mod = None
    gen_handraw_mod = None
    image_dalle3_mod = None
    image_sdiff_mod = None
    image_base_mod = None
    video_runway_mod = None
    video_base_mod = None
    handraw_base_mod = None
    handraw_chart_mod = None
    handraw_illus_mod = None

    for path, name, var_name in [
        (GEN_IMAGE_PY, 'gen_image', 'gen_image_mod'),
        (GEN_VIDEO_PY, 'gen_video', 'gen_video_mod'),
        (GEN_HANDRAW_PY, 'gen_handraw', 'gen_handraw_mod'),
        (IMAGE_BASE_PY, 'image_base', 'image_base_mod'),
        (IMAGE_DALLE3_PY, 'image_dalle3', 'image_dalle3_mod'),
        (IMAGE_SDIFF_PY, 'image_sdiffusion', 'image_sdiff_mod'),
        (VIDEO_BASE_PY, 'video_base', 'video_base_mod'),
        (VIDEO_RUNWAY_PY, 'video_runway', 'video_runway_mod'),
        (HANDRAW_BASE_PY, 'handraw_base', 'handraw_base_mod'),
        (HANDRAW_CHART_PY, 'handraw_chart_svg', 'handraw_chart_mod'),
        (HANDRAW_ILLUS_PY, 'handraw_illus_dalle', 'handraw_illus_mod'),
    ]:
        try:
            mod = load_module(path, name)
            locals()[var_name] = mod
            # Update the outer variables via assignment
            if var_name == 'gen_image_mod':
                gen_image_mod = mod
            elif var_name == 'gen_video_mod':
                gen_video_mod = mod
            elif var_name == 'gen_handraw_mod':
                gen_handraw_mod = mod
            elif var_name == 'image_base_mod':
                image_base_mod = mod
            elif var_name == 'image_dalle3_mod':
                image_dalle3_mod = mod
            elif var_name == 'image_sdiff_mod':
                image_sdiff_mod = mod
            elif var_name == 'video_base_mod':
                video_base_mod = mod
            elif var_name == 'video_runway_mod':
                video_runway_mod = mod
            elif var_name == 'handraw_base_mod':
                handraw_base_mod = mod
            elif var_name == 'handraw_chart_mod':
                handraw_chart_mod = mod
            elif var_name == 'handraw_illus_mod':
                handraw_illus_mod = mod
        except Exception as e:
            errors.append(f'Failed to import {name}: {e}')

    # ------------------------------------------------------------------ #
    # Test 1: DALL-E 3 image generation + script.json status update       #
    # Prompt: "programmer at desk, cinematic lighting"                    #
    # ------------------------------------------------------------------ #
    openai_key = os.environ.get('OPENAI_API_KEY', '')
    if not openai_key:
        print('OPENAI_API_KEY not set — skipping live DALL-E 3 image generation test', file=sys.stderr)
    elif gen_image_mod is None or image_dalle3_mod is None:
        errors.append('Test 1: gen_image or image_dalle3 module failed to load')
    else:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                script_data = make_script_with_scene('image', 'programmer at desk, cinematic lighting')
                script_path = os.path.join(tmpdir, 'script.json')
                with open(script_path, 'w') as f:
                    json.dump(script_data, f)

                output_path = os.path.join(tmpdir, 'scene_01_image.png')

                # Try calling generate function on gen_image module
                gen_fn = None
                for fn_name in ('generate_image', 'gen_image', 'generate', 'run', 'main'):
                    if hasattr(gen_image_mod, fn_name):
                        gen_fn = getattr(gen_image_mod, fn_name)
                        break

                # Also try provider class directly
                if gen_fn is None:
                    for cls_name in ('Dalle3ImageProvider', 'DALLE3Provider', 'DalleProvider'):
                        if hasattr(image_dalle3_mod, cls_name):
                            provider = getattr(image_dalle3_mod, cls_name)(api_key=openai_key)
                            if hasattr(provider, 'generate'):
                                gen_fn = lambda prompt, out, **kw: provider.generate(prompt, out, **kw)
                            break

                if gen_fn is None:
                    errors.append(
                        'Test 1: Could not find image generation function '
                        '(expected: generate_image, generate, or Dalle3ImageProvider.generate)'
                    )
                else:
                    try:
                        gen_fn(
                            'programmer at desk, cinematic lighting',
                            output_path,
                            provider='dalle3',
                            api_key=openai_key,
                        )
                    except TypeError:
                        try:
                            gen_fn('programmer at desk, cinematic lighting', output_path)
                        except Exception as e2:
                            errors.append(f'Test 1: generate_image raised: {e2}')
                            gen_fn = None

                    if gen_fn is not None:
                        valid, reason = is_valid_png(output_path)
                        if not valid:
                            errors.append(f'Test 1: Generated image invalid — {reason}')

                # Test script.json status update
                # Run gen_image with script.json to verify visual.status -> "ready"
                run_fn = None
                for fn_name in ('run', 'main', 'process_script', 'generate_for_script'):
                    if hasattr(gen_image_mod, fn_name):
                        run_fn = getattr(gen_image_mod, fn_name)
                        break

                if run_fn is not None:
                    try:
                        import unittest.mock as mock

                        # Mock the actual API call to return a fake image path
                        fake_img = os.path.join(tmpdir, 'fake_scene_01.png')
                        with open(fake_img, 'wb') as f:
                            f.write(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)

                        def mock_generate(*args, **kwargs):
                            return fake_img

                        # Patch provider-level generate functions
                        patch_targets = []
                        for mod in (gen_image_mod, image_dalle3_mod):
                            if mod is None:
                                continue
                            for fn_name in dir(mod):
                                if 'generat' in fn_name.lower() or 'dalle' in fn_name.lower():
                                    if callable(getattr(mod, fn_name, None)):
                                        patch_targets.append((mod, fn_name))

                        patches = [mock.patch.object(m, fn, mock_generate) for m, fn in patch_targets]
                        for p in patches:
                            try:
                                p.start()
                            except Exception:
                                pass

                        try:
                            try:
                                run_fn(script_path, tmpdir)
                            except TypeError:
                                run_fn(script_path)
                        except Exception as e:
                            print(f'Test 1: script run raised: {e}', file=sys.stderr)
                        finally:
                            for p in patches:
                                try:
                                    p.stop()
                                except Exception:
                                    pass

                        # Check script.json was updated
                        with open(script_path, 'r') as f:
                            updated = json.load(f)
                        scene = updated['scenes'][0]
                        status = scene.get('visual', {}).get('status', '')
                        if status not in ('ready', 'done', 'generated'):
                            # Acceptable if the implementation uses a different status name —
                            # check that it at least changed from 'pending'
                            if status == 'pending':
                                errors.append(
                                    f'Test 1: visual.status still "pending" after gen_image run; '
                                    'expected "ready" or "done"'
                                )
                    except Exception as e:
                        errors.append(f'Test 1: script.json status update test raised: {e}')
                else:
                    # Verify source has status update logic
                    with open(GEN_IMAGE_PY, 'r') as f:
                        src = f.read()
                    if 'status' not in src or ('ready' not in src and 'done' not in src):
                        errors.append(
                            'Test 1: gen_image.py does not appear to update visual.status '
                            '(expected "ready" or "done" assignment in source)'
                        )
        except Exception as e:
            errors.append(f'Test 1: DALL-E 3 image test raised unexpected exception: {e}')

    # ------------------------------------------------------------------ #
    # Test 2: Runway ML video generation + ffprobe duration check         #
    # Prompt: "code scrolling on screen", 5 seconds                      #
    # ------------------------------------------------------------------ #
    runway_key = os.environ.get('RUNWAY_API_KEY', '')
    if not runway_key:
        print('RUNWAY_API_KEY not set — skipping live Runway video generation test', file=sys.stderr)
    elif gen_video_mod is None or video_runway_mod is None:
        errors.append('Test 2: gen_video or video_runway module failed to load')
    else:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = os.path.join(tmpdir, 'scene_01_video.mp4')

                gen_fn = None
                for fn_name in ('generate_video', 'gen_video', 'generate', 'run', 'main'):
                    if hasattr(gen_video_mod, fn_name):
                        gen_fn = getattr(gen_video_mod, fn_name)
                        break

                if gen_fn is None:
                    for cls_name in ('RunwayVideoProvider', 'RunwayProvider', 'RunwayMLProvider'):
                        if hasattr(video_runway_mod, cls_name):
                            provider = getattr(video_runway_mod, cls_name)(api_key=runway_key)
                            if hasattr(provider, 'generate'):
                                gen_fn = lambda prompt, out, **kw: provider.generate(prompt, out, **kw)
                            break

                if gen_fn is None:
                    errors.append(
                        'Test 2: Could not find video generation function '
                        '(expected: generate_video, generate, or RunwayVideoProvider.generate)'
                    )
                else:
                    try:
                        gen_fn(
                            'code scrolling on screen',
                            output_path,
                            duration=5,
                            provider='runway',
                            api_key=runway_key,
                        )
                    except TypeError:
                        try:
                            gen_fn('code scrolling on screen', output_path, duration=5)
                        except Exception as e2:
                            errors.append(f'Test 2: generate_video raised: {e2}')
                            gen_fn = None

                    if gen_fn is not None:
                        if not os.path.exists(output_path):
                            errors.append(f'Test 2: Generated video file does not exist: {output_path}')
                        else:
                            # Verify ffprobe can read duration
                            try:
                                result = subprocess.run(
                                    ['ffprobe', '-v', 'quiet', '-print_format', 'json',
                                     '-show_streams', output_path],
                                    capture_output=True, text=True, timeout=30
                                )
                                if result.returncode != 0:
                                    errors.append(
                                        f'Test 2: ffprobe failed on generated video: {result.stderr}'
                                    )
                                else:
                                    probe_data = json.loads(result.stdout)
                                    streams = probe_data.get('streams', [])
                                    if not streams:
                                        errors.append('Test 2: ffprobe found no streams in video')
                                    else:
                                        duration = float(streams[0].get('duration', 0))
                                        if duration <= 0:
                                            errors.append(
                                                f'Test 2: Video duration is {duration}s, expected > 0'
                                            )
                            except FileNotFoundError:
                                print('ffprobe not found — skipping duration check', file=sys.stderr)
                            except Exception as e:
                                errors.append(f'Test 2: ffprobe check raised: {e}')
        except Exception as e:
            errors.append(f'Test 2: Runway video test raised unexpected exception: {e}')

    # ------------------------------------------------------------------ #
    # Test 3: handraw_chart — SVG→PNG, no Node.js, contains line+axes    #
    # Subject: "程序员数量逐年下降趋势折线图"                             #
    # ------------------------------------------------------------------ #
    if gen_handraw_mod is None or handraw_chart_mod is None:
        errors.append('Test 3: gen_handraw or handraw_chart_svg module failed to load')
    else:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = os.path.join(tmpdir, 'chart_output.png')

                # Find generate function for handraw_chart type
                gen_fn = None
                for fn_name in ('generate', 'generate_handraw', 'gen_handraw',
                                'generate_chart', 'run', 'main'):
                    if hasattr(gen_handraw_mod, fn_name):
                        gen_fn = getattr(gen_handraw_mod, fn_name)
                        break

                # Also try chart provider directly
                chart_gen_fn = None
                for cls_name in ('HandrawChartSVGProvider', 'ChartSVGProvider', 'ChartProvider'):
                    if hasattr(handraw_chart_mod, cls_name):
                        provider = getattr(handraw_chart_mod, cls_name)()
                        if hasattr(provider, 'generate'):
                            chart_gen_fn = provider.generate
                        break
                if chart_gen_fn is None:
                    for fn_name in ('generate', 'generate_chart', 'chart_to_png', 'svg_to_png'):
                        if hasattr(handraw_chart_mod, fn_name):
                            chart_gen_fn = getattr(handraw_chart_mod, fn_name)
                            break

                called_fn = chart_gen_fn or gen_fn
                if called_fn is None:
                    errors.append(
                        'Test 3: Could not find chart generation function '
                        '(expected: HandrawChartSVGProvider.generate or generate_chart)'
                    )
                else:
                    try:
                        called_fn(
                            '程序员数量逐年下降趋势折线图',
                            output_path,
                            handraw_type='handraw_chart',
                        )
                    except TypeError:
                        try:
                            called_fn('程序员数量逐年下降趋势折线图', output_path)
                        except Exception as e2:
                            errors.append(f'Test 3: chart generation raised: {e2}')
                            called_fn = None

                    if called_fn is not None:
                        valid, reason = is_valid_png(output_path)
                        if not valid:
                            errors.append(f'Test 3: Chart output is not a valid PNG — {reason}')
                        else:
                            # Verify no Node.js was required (check source for node/npm references)
                            with open(HANDRAW_CHART_PY, 'r') as f:
                                src = f.read()
                            if 'node ' in src.lower() or 'npm ' in src.lower() or 'nodejs' in src.lower():
                                errors.append(
                                    'Test 3: handraw_chart_svg.py references Node.js/npm, '
                                    'but requirement is pure Python (cairosvg)'
                                )
                            # Verify cairosvg or SVG approach is used
                            if 'cairosvg' not in src and 'svg' not in src.lower():
                                errors.append(
                                    'Test 3: handraw_chart_svg.py does not appear to use '
                                    'cairosvg or SVG approach (expected LLM→SVG→PNG pipeline)'
                                )
                            # Check PNG has reasonable size (chart should have content)
                            size = os.path.getsize(output_path)
                            if size < 1000:
                                errors.append(
                                    f'Test 3: Chart PNG is only {size} bytes — '
                                    'likely empty or minimal content'
                                )
        except Exception as e:
            errors.append(f'Test 3: handraw_chart test raised unexpected exception: {e}')

    # ------------------------------------------------------------------ #
    # Test 4: handraw_illustration — DALL-E 3 hand-drawn style            #
    # Subject: "AI 机器人取代程序员的示意图"                              #
    # ------------------------------------------------------------------ #
    if not openai_key:
        print('OPENAI_API_KEY not set — skipping live handraw_illustration test', file=sys.stderr)
    elif gen_handraw_mod is None or handraw_illus_mod is None:
        errors.append('Test 4: gen_handraw or handraw_illus_dalle module failed to load')
    else:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = os.path.join(tmpdir, 'illus_output.png')

                # Find generate function for handraw_illustration type
                illus_gen_fn = None
                for cls_name in ('HandrawIllusDalleProvider', 'IllusDalleProvider', 'IllusProvider'):
                    if hasattr(handraw_illus_mod, cls_name):
                        provider = getattr(handraw_illus_mod, cls_name)(api_key=openai_key)
                        if hasattr(provider, 'generate'):
                            illus_gen_fn = provider.generate
                        break
                if illus_gen_fn is None:
                    for fn_name in ('generate', 'generate_illustration', 'illus_to_png'):
                        if hasattr(handraw_illus_mod, fn_name):
                            illus_gen_fn = getattr(handraw_illus_mod, fn_name)
                            break

                gen_fn = None
                for fn_name in ('generate', 'generate_handraw', 'gen_handraw', 'run', 'main'):
                    if hasattr(gen_handraw_mod, fn_name):
                        gen_fn = getattr(gen_handraw_mod, fn_name)
                        break

                called_fn = illus_gen_fn or gen_fn
                if called_fn is None:
                    errors.append(
                        'Test 4: Could not find illustration generation function '
                        '(expected: HandrawIllusDalleProvider.generate or generate_handraw)'
                    )
                else:
                    try:
                        called_fn(
                            'AI 机器人取代程序员的示意图',
                            output_path,
                            handraw_type='handraw_illustration',
                            api_key=openai_key,
                        )
                    except TypeError:
                        try:
                            called_fn('AI 机器人取代程序员的示意图', output_path)
                        except Exception as e2:
                            errors.append(f'Test 4: illustration generation raised: {e2}')
                            called_fn = None

                    if called_fn is not None:
                        valid, reason = is_valid_png(output_path)
                        if not valid:
                            errors.append(
                                f'Test 4: Illustration output is not a valid PNG — {reason}'
                            )
                        else:
                            # Verify hand-drawn style prompt is used in source
                            with open(HANDRAW_ILLUS_PY, 'r') as f:
                                src = f.read()
                            hand_drawn_keywords = [
                                'hand-drawn', 'hand drawn', 'sketch', 'pencil', 'handraw',
                                'illustration', 'doodle', 'ink', 'watercolor',
                            ]
                            has_style = any(kw in src.lower() for kw in hand_drawn_keywords)
                            if not has_style:
                                errors.append(
                                    'Test 4: handraw_illus_dalle.py does not appear to inject '
                                    'hand-drawn style into the DALL-E 3 prompt '
                                    '(expected keywords: hand-drawn, sketch, pencil, etc.)'
                                )
                            # Verify DALL-E 3 is used
                            if 'dall-e-3' not in src and 'dalle3' not in src.lower() and 'dall_e_3' not in src:
                                errors.append(
                                    'Test 4: handraw_illus_dalle.py does not appear to use '
                                    'DALL-E 3 model (expected "dall-e-3" in source)'
                                )
        except Exception as e:
            errors.append(f'Test 4: handraw_illustration test raised unexpected exception: {e}')

    # ------------------------------------------------------------------ #
    # Test 5a: Provider switching — dalle3 → stable_diffusion             #
    # ------------------------------------------------------------------ #
    if gen_image_mod is None or image_sdiff_mod is None:
        errors.append('Test 5a: gen_image or image_sdiffusion module failed to load')
    else:
        try:
            # Verify Protocol/base interface is defined
            with open(IMAGE_BASE_PY, 'r') as f:
                base_src = f.read()
            has_protocol = any(kw in base_src for kw in ['Protocol', 'ABC', 'abstractmethod', 'def generate'])
            if not has_protocol:
                errors.append(
                    'Test 5a: image_base.py does not define a Protocol/ABC interface '
                    '(expected Protocol class with generate method)'
                )

            # Verify stable_diffusion provider implements the interface
            with open(IMAGE_SDIFF_PY, 'r') as f:
                sdiff_src = f.read()
            has_generate = 'def generate' in sdiff_src
            if not has_generate:
                errors.append(
                    'Test 5a: image_sdiffusion.py does not implement generate() method'
                )

            # Verify gen_image.py supports provider selection
            with open(GEN_IMAGE_PY, 'r') as f:
                gen_src = f.read()
            has_provider_switch = any(kw in gen_src for kw in [
                'provider', 'stable_diffusion', 'sdiffusion', 'dalle3', 'DALL',
                'get_provider', 'provider_map', 'provider_cls',
            ])
            if not has_provider_switch:
                errors.append(
                    'Test 5a: gen_image.py does not appear to support provider switching '
                    '(expected provider selection logic for dalle3/stable_diffusion)'
                )

            # Test: call gen_image with provider='stable_diffusion' using a mock
            import unittest.mock as mock

            gen_fn = None
            for fn_name in ('generate_image', 'gen_image', 'generate', 'run', 'main'):
                if hasattr(gen_image_mod, fn_name):
                    gen_fn = getattr(gen_image_mod, fn_name)
                    break

            if gen_fn is not None:
                with tempfile.TemporaryDirectory() as tmpdir:
                    output_path = os.path.join(tmpdir, 'sdiff_output.png')
                    fake_img = os.path.join(tmpdir, 'fake.png')
                    with open(fake_img, 'wb') as f:
                        f.write(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)

                    # Mock the stable diffusion provider's generate to return fake_img
                    called_with_sdiff = []

                    def mock_sdiff_generate(*args, **kwargs):
                        called_with_sdiff.append(True)
                        return fake_img

                    patch_targets = []
                    for fn_name in dir(image_sdiff_mod):
                        if 'generat' in fn_name.lower() or 'stable' in fn_name.lower():
                            if callable(getattr(image_sdiff_mod, fn_name, None)):
                                patch_targets.append(fn_name)

                    # Also try patching a class method
                    for cls_name in ('StableDiffusionProvider', 'SDiffusionProvider',
                                     'StableDiffusionImageProvider'):
                        if hasattr(image_sdiff_mod, cls_name):
                            cls = getattr(image_sdiff_mod, cls_name)
                            if hasattr(cls, 'generate'):
                                with mock.patch.object(cls, 'generate', mock_sdiff_generate):
                                    try:
                                        gen_fn(
                                            'test prompt',
                                            output_path,
                                            provider='stable_diffusion',
                                        )
                                        # If no exception, provider switching works
                                    except Exception as e:
                                        # Acceptable if API key is missing — check error message
                                        msg = str(e).lower()
                                        if 'api' not in msg and 'key' not in msg and 'provider' not in msg:
                                            errors.append(
                                                f'Test 5a: gen_image with provider=stable_diffusion '
                                                f'raised unexpected error: {e}'
                                            )
                            break
        except Exception as e:
            errors.append(f'Test 5a: provider switching test raised unexpected exception: {e}')

    # ------------------------------------------------------------------ #
    # Test 5b: Mock handraw provider — extensibility without modifying    #
    # gen_handraw.py                                                       #
    # ------------------------------------------------------------------ #
    if handraw_base_mod is None or gen_handraw_mod is None:
        errors.append('Test 5b: handraw_base or gen_handraw module failed to load')
    else:
        try:
            # Verify handraw_base defines a Protocol/interface
            with open(HANDRAW_BASE_PY, 'r') as f:
                base_src = f.read()
            has_protocol = any(kw in base_src for kw in ['Protocol', 'ABC', 'abstractmethod', 'def generate'])
            if not has_protocol:
                errors.append(
                    'Test 5b: handraw_base.py does not define a Protocol/ABC interface '
                    '(expected Protocol class with generate method)'
                )

            # Verify gen_handraw.py uses dependency injection / provider lookup
            with open(GEN_HANDRAW_PY, 'r') as f:
                gen_src = f.read()
            has_di = any(kw in gen_src for kw in [
                'provider', 'handraw_type', 'chart', 'illustration',
                'get_provider', 'provider_map', 'registry',
            ])
            if not has_di:
                errors.append(
                    'Test 5b: gen_handraw.py does not appear to implement provider routing '
                    '(expected handraw_type routing: chart→chart_svg, illustration→illus_dalle)'
                )

            # Create a mock provider that implements handraw_base Protocol
            mock_output_path = None

            class MockHandrawProvider:
                """Mock provider implementing handraw_base Protocol."""
                def generate(self, subject: str, output_path: str, **kwargs) -> str:
                    nonlocal mock_output_path
                    # Write a fake PNG
                    with open(output_path, 'wb') as f:
                        f.write(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
                    mock_output_path = output_path
                    return output_path

            mock_provider = MockHandrawProvider()

            # Try to inject the mock provider into gen_handraw
            gen_fn = None
            for fn_name in ('generate', 'generate_handraw', 'gen_handraw', 'run', 'main'):
                if hasattr(gen_handraw_mod, fn_name):
                    gen_fn = getattr(gen_handraw_mod, fn_name)
                    break

            if gen_fn is None:
                errors.append(
                    'Test 5b: Could not find generate function in gen_handraw.py'
                )
            else:
                import unittest.mock as mock

                with tempfile.TemporaryDirectory() as tmpdir:
                    output_path = os.path.join(tmpdir, 'mock_output.png')

                    # Try to inject mock provider via provider_map or registry
                    injected = False

                    # Method 1: provider_map dict
                    for attr_name in ('provider_map', 'PROVIDER_MAP', 'providers', 'PROVIDERS',
                                      'handraw_registry', 'REGISTRY'):
                        if hasattr(gen_handraw_mod, attr_name):
                            provider_map = getattr(gen_handraw_mod, attr_name)
                            if isinstance(provider_map, dict):
                                original = dict(provider_map)
                                provider_map['mock_type'] = MockHandrawProvider
                                try:
                                    gen_fn(
                                        'test subject',
                                        output_path,
                                        handraw_type='mock_type',
                                    )
                                    if os.path.exists(output_path):
                                        injected = True
                                except Exception as e:
                                    print(f'Test 5b: mock injection via {attr_name} raised: {e}',
                                          file=sys.stderr)
                                finally:
                                    provider_map.clear()
                                    provider_map.update(original)
                                break

                    # Method 2: try calling with provider instance directly
                    if not injected:
                        try:
                            gen_fn(
                                'test subject',
                                output_path,
                                provider=mock_provider,
                            )
                            if os.path.exists(output_path):
                                injected = True
                        except Exception:
                            pass

                    if not injected:
                        # Verify source code supports extensibility at minimum
                        extensible_keywords = [
                            'provider_map', 'registry', 'get_provider', 'provider_cls',
                            'handraw_type', 'chart_svg', 'illus_dalle',
                        ]
                        has_extensibility = any(kw in gen_src for kw in extensible_keywords)
                        if not has_extensibility:
                            errors.append(
                                'Test 5b: gen_handraw.py does not appear to support extensible '
                                'provider injection (expected provider_map, registry, or '
                                'get_provider pattern for adding new providers without '
                                'modifying gen_handraw.py)'
                            )
                        else:
                            print(
                                'Test 5b: Provider injection not directly testable, '
                                'but extensibility pattern found in source.',
                                file=sys.stderr
                            )
        except Exception as e:
            errors.append(f'Test 5b: mock provider extensibility test raised unexpected exception: {e}')

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
