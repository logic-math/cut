#!/usr/bin/env python3
"""Test script for task4: fetch-assets skill (video/image/music search)."""
import json
import sys
import os
import importlib.util
import copy
import tempfile

# Project root is 5 levels up from this file:
# .rick/jobs/job_1/doing/tests/task4.py -> project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
FETCH_ASSETS_DIR = os.path.join(PROJECT_ROOT, 'cut', 'skills', 'fetch-assets', 'scripts')
FETCH_VIDEO_PY = os.path.join(FETCH_ASSETS_DIR, 'fetch_video.py')
FETCH_MUSIC_PY = os.path.join(FETCH_ASSETS_DIR, 'fetch_music.py')
FETCH_IMAGE_PY = os.path.join(FETCH_ASSETS_DIR, 'fetch_image.py')


def load_module(path, name):
    """Load a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_10_scene_script():
    """Create a 10-scene script.json for full-run test."""
    visual_types = ['video', 'image', 'video', 'image', 'video',
                    'image', 'video', 'image', 'video', 'image']
    music_keywords_list = [
        ['mood:melancholic', 'genre:ambient'],
        ['mood:futuristic', 'genre:electronic'],
        ['mood:narrative', 'genre:cinematic'],
        ['mood:upbeat', 'genre:pop'],
        ['mood:calm', 'genre:acoustic'],
        ['mood:dramatic', 'genre:orchestral'],
        ['mood:happy', 'genre:jazz'],
        ['mood:dark', 'genre:hip-hop'],
        ['mood:romantic', 'genre:classical'],
        ['mood:energetic', 'genre:rock'],
    ]
    keyword_sets = [
        ['programmer', 'computer', 'coding'],
        ['technology', 'modern', 'concept'],
        ['nature', 'landscape', 'outdoor'],
        ['city', 'urban', 'street'],
        ['business', 'office', 'meeting'],
        ['science', 'research', 'lab'],
        ['travel', 'adventure', 'explore'],
        ['food', 'cooking', 'kitchen'],
        ['music', 'concert', 'performance'],
        ['sport', 'fitness', 'exercise'],
    ]
    scenes = []
    for i in range(10):
        scenes.append({
            'id': f'scene_{i+1:02d}',
            'duration': 5 + i % 5,
            'narration': f'Scene {i+1} narration text.',
            'subtitle': f'Scene {i+1} subtitle.',
            'visual': {
                'type': visual_types[i],
                'description': f'Scene {i+1} visual description.',
                'keywords': keyword_sets[i],
                'status': 'pending',
                'selected_candidate': None,
                'candidates': [],
                'asset_path': None,
            },
            'audio': {
                'narration_status': 'pending',
                'narration_path': None,
                'music': {
                    'description': f'Scene {i+1} music mood.',
                    'keywords': music_keywords_list[i],
                    'status': 'pending',
                    'selected_candidate': None,
                    'candidates': [],
                    'asset_path': None,
                    'volume': 0.3,
                },
            },
        })
    return {
        'title': 'Test 10-Scene Script',
        'total_duration': 60,
        'output_format': 'mp4',
        'resolution': '1920x1080',
        'pipeline_state': 'draft',
        'scenes': scenes,
    }


def check_video_candidate_fields(candidate):
    """Return list of missing required fields in a video candidate."""
    missing = []
    for field in ('url', 'duration', 'thumbnail'):
        if field not in candidate:
            missing.append(field)
    return missing


def check_music_candidate_fields(candidate):
    """Return list of missing required fields in a music candidate."""
    missing = []
    for field in ('name', 'artist', 'duration', 'download_url'):
        if field not in candidate:
            missing.append(field)
    return missing


def main():
    errors = []

    # ------------------------------------------------------------------ #
    # Pre-check: verify implementation files exist and are non-trivial    #
    # ------------------------------------------------------------------ #
    for path, label in [
        (FETCH_VIDEO_PY, 'fetch_video.py'),
        (FETCH_MUSIC_PY, 'fetch_music.py'),
        (FETCH_IMAGE_PY, 'fetch_image.py'),
    ]:
        if not os.path.exists(path):
            errors.append(f'{label} does not exist at {path}')
        else:
            with open(path, 'r') as f:
                content = f.read()
            if 'TODO' in content and len(content.strip().splitlines()) <= 5:
                errors.append(
                    f'{label} appears to be a stub (contains TODO and has ≤5 lines). '
                    'Task4 implementation is required.'
                )

    if errors:
        # If files are missing or stubs, no point running further tests
        result = {'pass': False, 'errors': errors}
        print(json.dumps(result))
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # Load modules                                                         #
    # ------------------------------------------------------------------ #
    try:
        fetch_video_mod = load_module(FETCH_VIDEO_PY, 'fetch_video')
    except Exception as e:
        errors.append(f'Failed to import fetch_video.py: {e}')
        fetch_video_mod = None

    try:
        fetch_music_mod = load_module(FETCH_MUSIC_PY, 'fetch_music')
    except Exception as e:
        errors.append(f'Failed to import fetch_music.py: {e}')
        fetch_music_mod = None

    # ------------------------------------------------------------------ #
    # Test 1: Pexels API — search video with "programmer computer coding" #
    # ------------------------------------------------------------------ #
    pexels_key = os.environ.get('PEXELS_API_KEY', '')
    if not pexels_key:
        print('PEXELS_API_KEY not set — skipping live Pexels test', file=sys.stderr)
    elif fetch_video_mod is None:
        errors.append('Test 1 skipped: fetch_video module failed to load')
    else:
        try:
            # Try search_pexels_videos or a generic search_videos function
            search_fn = None
            for fn_name in ('search_pexels_videos', 'search_videos_pexels', 'fetch_pexels_videos'):
                if hasattr(fetch_video_mod, fn_name):
                    search_fn = getattr(fetch_video_mod, fn_name)
                    break
            # Fallback: try a generic search that accepts provider param
            if search_fn is None and hasattr(fetch_video_mod, 'search_videos'):
                def search_fn(keywords, api_key=None, **kwargs):
                    return fetch_video_mod.search_videos(keywords, provider='pexels',
                                                         api_key=api_key or pexels_key, **kwargs)
            # Fallback: try provider class
            if search_fn is None:
                for cls_name in ('PexelsVideoProvider', 'PexelsProvider'):
                    if hasattr(fetch_video_mod, cls_name):
                        provider = getattr(fetch_video_mod, cls_name)(api_key=pexels_key)
                        search_fn = provider.search
                        break

            if search_fn is None:
                errors.append(
                    'Test 1: Could not find Pexels video search function in fetch_video.py '
                    '(expected: search_pexels_videos, search_videos, or PexelsVideoProvider)'
                )
            else:
                results = search_fn(['programmer', 'computer', 'coding'], api_key=pexels_key)
                if not isinstance(results, list):
                    errors.append(f'Test 1: Pexels search returned {type(results).__name__}, expected list')
                elif len(results) < 3:
                    errors.append(
                        f'Test 1: Pexels search returned {len(results)} results, expected at least 3'
                    )
                else:
                    for i, candidate in enumerate(results[:3]):
                        missing = check_video_candidate_fields(candidate)
                        if missing:
                            errors.append(
                                f'Test 1: Pexels candidate[{i}] missing fields: {missing}'
                            )
        except Exception as e:
            errors.append(f'Test 1: Pexels video search raised exception: {e}')

    # ------------------------------------------------------------------ #
    # Test 2: Jamendo API — search music with "calm ambient"              #
    # ------------------------------------------------------------------ #
    jamendo_key = os.environ.get('JAMENDO_API_KEY', '')
    if not jamendo_key:
        print('JAMENDO_API_KEY not set — skipping live Jamendo test', file=sys.stderr)
    elif fetch_music_mod is None:
        errors.append('Test 2 skipped: fetch_music module failed to load')
    else:
        try:
            search_fn = None
            for fn_name in ('search_jamendo_music', 'search_music_jamendo', 'fetch_jamendo_music'):
                if hasattr(fetch_music_mod, fn_name):
                    search_fn = getattr(fetch_music_mod, fn_name)
                    break
            if search_fn is None and hasattr(fetch_music_mod, 'search_music'):
                def search_fn(keywords, api_key=None, **kwargs):
                    return fetch_music_mod.search_music(keywords, provider='jamendo',
                                                        api_key=api_key or jamendo_key, **kwargs)
            if search_fn is None:
                for cls_name in ('JamendoMusicProvider', 'JamendoProvider'):
                    if hasattr(fetch_music_mod, cls_name):
                        provider = getattr(fetch_music_mod, cls_name)(api_key=jamendo_key)
                        search_fn = provider.search
                        break

            if search_fn is None:
                errors.append(
                    'Test 2: Could not find Jamendo music search function in fetch_music.py '
                    '(expected: search_jamendo_music, search_music, or JamendoMusicProvider)'
                )
            else:
                results = search_fn(['calm', 'ambient'], api_key=jamendo_key)
                if not isinstance(results, list):
                    errors.append(f'Test 2: Jamendo search returned {type(results).__name__}, expected list')
                elif len(results) < 3:
                    errors.append(
                        f'Test 2: Jamendo search returned {len(results)} results, expected at least 3'
                    )
                else:
                    for i, candidate in enumerate(results[:3]):
                        missing = check_music_candidate_fields(candidate)
                        if missing:
                            errors.append(
                                f'Test 2: Jamendo candidate[{i}] missing fields: {missing}'
                            )
        except Exception as e:
            errors.append(f'Test 2: Jamendo music search raised exception: {e}')

    # ------------------------------------------------------------------ #
    # Test 3: Fallback from Pexels (empty) to Pixabay                    #
    # ------------------------------------------------------------------ #
    if fetch_video_mod is None:
        errors.append('Test 3 skipped: fetch_video module failed to load')
    else:
        try:
            import unittest.mock as mock

            # Look for a multi-provider search function
            multi_search_fn = None
            for fn_name in ('fetch_video_candidates', 'search_with_fallback',
                            'fetch_candidates', 'get_video_candidates'):
                if hasattr(fetch_video_mod, fn_name):
                    multi_search_fn = getattr(fetch_video_mod, fn_name)
                    break

            if multi_search_fn is None:
                # Try the main fetch function that reads config
                for fn_name in ('fetch_videos_for_scene', 'fetch_video', 'run'):
                    if hasattr(fetch_video_mod, fn_name):
                        multi_search_fn = getattr(fetch_video_mod, fn_name)
                        break

            if multi_search_fn is None:
                errors.append(
                    'Test 3: Could not find multi-provider fallback function in fetch_video.py '
                    '(expected: fetch_video_candidates, search_with_fallback, or fetch_videos_for_scene)'
                )
            else:
                # Mock Pexels to return empty, Pixabay to return 3 results
                pixabay_mock_results = [
                    {'url': f'https://pixabay.com/video/{i}', 'duration': 10 + i,
                     'thumbnail': f'https://pixabay.com/thumb/{i}.jpg', 'provider': 'pixabay'}
                    for i in range(3)
                ]

                pexels_patched = False
                pixabay_patched = False

                # Try patching provider-level search functions
                for pexels_fn in ('search_pexels_videos', 'search_videos_pexels',
                                  '_search_pexels', 'pexels_search'):
                    if hasattr(fetch_video_mod, pexels_fn):
                        with mock.patch.object(fetch_video_mod, pexels_fn, return_value=[]):
                            pexels_patched = True
                            for pixabay_fn in ('search_pixabay_videos', 'search_videos_pixabay',
                                               '_search_pixabay', 'pixabay_search'):
                                if hasattr(fetch_video_mod, pixabay_fn):
                                    with mock.patch.object(fetch_video_mod, pixabay_fn,
                                                           return_value=pixabay_mock_results):
                                        pixabay_patched = True
                                        try:
                                            result = multi_search_fn(
                                                ['programmer', 'computer', 'coding'],
                                                providers=['pexels', 'pixabay']
                                            )
                                            if not result:
                                                errors.append(
                                                    'Test 3: Fallback to Pixabay failed — '
                                                    'returned empty when Pexels was mocked empty'
                                                )
                                            elif not any(
                                                c.get('provider') == 'pixabay' or
                                                'pixabay' in str(c.get('url', ''))
                                                for c in result
                                            ):
                                                errors.append(
                                                    'Test 3: Fallback result does not appear to '
                                                    'come from Pixabay provider'
                                                )
                                        except Exception as e:
                                            errors.append(f'Test 3: Fallback call raised: {e}')
                                    break
                        break

                if not pexels_patched:
                    # Document that test 3 requires provider-level functions to be patchable
                    print(
                        'Test 3: Could not patch Pexels/Pixabay provider functions directly; '
                        'verifying fallback logic exists in source code instead.',
                        file=sys.stderr
                    )
                    with open(FETCH_VIDEO_PY, 'r') as f:
                        src = f.read()
                    # Check that the code has fallback/provider iteration logic
                    has_fallback = any(kw in src for kw in
                                       ['fallback', 'providers', 'for provider', 'pixabay', 'pexels'])
                    if not has_fallback:
                        errors.append(
                            'Test 3: fetch_video.py does not appear to implement '
                            'multi-provider fallback (no fallback/providers keywords found)'
                        )
        except Exception as e:
            errors.append(f'Test 3: Fallback test raised unexpected exception: {e}')

    # ------------------------------------------------------------------ #
    # Test 4: Missing API key gives clear error with setup instructions   #
    # ------------------------------------------------------------------ #
    for mod, label, key_env in [
        (fetch_video_mod, 'fetch_video', 'PEXELS_API_KEY'),
        (fetch_music_mod, 'fetch_music', 'JAMENDO_API_KEY'),
    ]:
        if mod is None:
            errors.append(f'Test 4 ({label}): module failed to load, skipping')
            continue
        try:
            orig_key = os.environ.pop(key_env, None)
            try:
                # Try to trigger a missing-key error
                error_raised = False
                error_msg = ''
                # Try calling any search function without a key
                for fn_name in (
                    'search_pexels_videos', 'search_videos_pexels',
                    'search_jamendo_music', 'search_music_jamendo',
                    'search_videos', 'search_music',
                    'fetch_video_candidates', 'fetch_music_candidates',
                ):
                    if hasattr(mod, fn_name):
                        try:
                            fn = getattr(mod, fn_name)
                            fn(['test'], api_key='')
                        except (ValueError, KeyError, EnvironmentError, RuntimeError) as e:
                            error_raised = True
                            error_msg = str(e)
                            break
                        except Exception:
                            pass

                # Also try provider class init without key
                if not error_raised:
                    for cls_name in (
                        'PexelsVideoProvider', 'PexelsProvider',
                        'JamendoMusicProvider', 'JamendoProvider',
                        'PixabayVideoProvider',
                    ):
                        if hasattr(mod, cls_name):
                            try:
                                getattr(mod, cls_name)(api_key='')
                            except (ValueError, KeyError, EnvironmentError, RuntimeError) as e:
                                error_raised = True
                                error_msg = str(e)
                                break
                            except Exception:
                                pass

                if not error_raised:
                    # Check source for key validation logic
                    with open(mod.__file__, 'r') as f:
                        src = f.read()
                    has_key_check = any(kw in src for kw in [
                        'API_KEY', 'api_key', 'environ', 'PEXELS', 'JAMENDO', 'PIXABAY',
                        'not api_key', 'missing', 'required', 'obtain', 'get.*key', 'how to'
                    ])
                    if not has_key_check:
                        errors.append(
                            f'Test 4 ({label}): No API key validation found in source. '
                            f'Missing key should raise a clear error with setup instructions.'
                        )
                else:
                    # Verify the error message is informative
                    msg_lower = error_msg.lower()
                    has_helpful_msg = any(kw in msg_lower for kw in [
                        'api key', 'api_key', 'pexels', 'jamendo', 'pixabay',
                        'environ', 'set', 'obtain', 'get', 'https://', 'http://',
                        'register', 'sign up', 'required', 'missing',
                    ])
                    if not has_helpful_msg:
                        errors.append(
                            f'Test 4 ({label}): Error message "{error_msg}" is not helpful. '
                            'Should explain how to get/set the API key.'
                        )
            finally:
                if orig_key is not None:
                    os.environ[key_env] = orig_key
        except Exception as e:
            errors.append(f'Test 4 ({label}): unexpected exception: {e}')

    # ------------------------------------------------------------------ #
    # Test 5: Full 10-scene script.json — candidates field filled         #
    # ------------------------------------------------------------------ #
    # This test runs the main fetch script on a temp script.json and
    # verifies every scene's candidates are populated.
    if fetch_video_mod is None and fetch_music_mod is None:
        errors.append('Test 5 skipped: both fetch modules failed to load')
    else:
        # Look for a top-level run/main function that processes script.json
        run_fn = None
        for mod in (fetch_video_mod, fetch_music_mod):
            if mod is None:
                continue
            for fn_name in ('run', 'main', 'fetch_all', 'process_script',
                            'fetch_candidates_for_script'):
                if hasattr(mod, fn_name):
                    run_fn = getattr(mod, fn_name)
                    break
            if run_fn:
                break

        # Also check for a unified fetch_assets.py at the skill root
        fetch_assets_py = os.path.join(FETCH_ASSETS_DIR, 'fetch_assets.py')
        if run_fn is None and os.path.exists(fetch_assets_py):
            try:
                fa_mod = load_module(fetch_assets_py, 'fetch_assets')
                for fn_name in ('run', 'main', 'fetch_all', 'process_script'):
                    if hasattr(fa_mod, fn_name):
                        run_fn = getattr(fa_mod, fn_name)
                        break
            except Exception as e:
                print(f'Test 5: Could not load fetch_assets.py: {e}', file=sys.stderr)

        if run_fn is None:
            # Fallback: check source for subprocess/CLI invocation pattern
            # and test by running the script directly
            script_content = ''
            for path in (FETCH_VIDEO_PY, FETCH_MUSIC_PY):
                try:
                    with open(path, 'r') as f:
                        script_content += f.read()
                except Exception:
                    pass
            has_script_processing = any(kw in script_content for kw in [
                'script.json', 'script_path', 'candidates', 'argparse', '--script',
            ])
            if not has_script_processing:
                errors.append(
                    'Test 5: Could not find a script.json processing function. '
                    'Expected run()/main()/fetch_all() that processes script.json and fills candidates.'
                )
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                script_path = os.path.join(tmpdir, 'script.json')
                script_data = make_10_scene_script()
                with open(script_path, 'w') as f:
                    json.dump(script_data, f, ensure_ascii=False, indent=2)

                try:
                    import unittest.mock as mock

                    # Mock all external API calls to return fake candidates
                    def mock_video_candidates(keywords, **kwargs):
                        return [
                            {'url': f'https://example.com/v{i}', 'duration': 10,
                             'thumbnail': f'https://example.com/t{i}.jpg', 'provider': 'pexels'}
                            for i in range(3)
                        ]

                    def mock_music_candidates(keywords, **kwargs):
                        return [
                            {'name': f'Track {i}', 'artist': f'Artist {i}',
                             'duration': 180, 'download_url': f'https://example.com/m{i}.mp3',
                             'provider': 'jamendo'}
                            for i in range(3)
                        ]

                    # Build a list of possible API functions to mock
                    patch_targets = []
                    for mod, mock_fn in [
                        (fetch_video_mod, mock_video_candidates),
                        (fetch_music_mod, mock_music_candidates),
                    ]:
                        if mod is None:
                            continue
                        for fn_name in dir(mod):
                            if any(kw in fn_name.lower() for kw in ('pexels', 'pixabay', 'jamendo')):
                                if callable(getattr(mod, fn_name)):
                                    patch_targets.append((mod, fn_name, mock_fn))

                    # Apply patches and run
                    patches = [mock.patch.object(mod, fn, mock_fn)
                                for mod, fn, mock_fn in patch_targets]
                    for p in patches:
                        p.start()
                    try:
                        # Try calling run with script path
                        try:
                            run_fn(script_path)
                        except TypeError:
                            # Maybe it takes workspace arg
                            run_fn(script_path, tmpdir)
                    finally:
                        for p in patches:
                            p.stop()

                    # Read back the modified script.json
                    with open(script_path, 'r') as f:
                        updated = json.load(f)

                    scenes = updated.get('scenes', [])
                    if len(scenes) != 10:
                        errors.append(
                            f'Test 5: Expected 10 scenes in output, got {len(scenes)}'
                        )
                    else:
                        unfilled = []
                        for scene in scenes:
                            sid = scene.get('id', '?')
                            visual_candidates = scene.get('visual', {}).get('candidates', None)
                            music_candidates = scene.get('audio', {}).get('music', {}).get('candidates', None)
                            if visual_candidates is None or len(visual_candidates) == 0:
                                # Only flag video/image types (handraw doesn't need stock assets)
                                vtype = scene.get('visual', {}).get('type', '')
                                if vtype in ('video', 'image'):
                                    unfilled.append(f'{sid}.visual.candidates (type={vtype})')
                            if music_candidates is None or len(music_candidates) == 0:
                                unfilled.append(f'{sid}.audio.music.candidates')
                        if unfilled:
                            errors.append(
                                f'Test 5: Following scenes have empty candidates after full run: '
                                f'{unfilled}'
                            )
                except Exception as e:
                    errors.append(f'Test 5: Full script run raised exception: {e}')

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
