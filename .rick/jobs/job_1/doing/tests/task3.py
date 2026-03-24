#!/usr/bin/env python3
"""Test script for task3: TTS service abstraction layer and gen-audio-tts skill."""
import json
import sys
import os
import subprocess
import tempfile
import shutil

# Project root: tests/ -> doing/ -> job_1/ -> jobs/ -> .rick/ -> cut/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
GEN_ASSETS_DIR = os.path.join(PROJECT_ROOT, 'cut', 'skills', 'gen-assets', 'scripts')
PROVIDERS_DIR = os.path.join(GEN_ASSETS_DIR, 'providers')
CUT_CONFIG = os.path.join(PROJECT_ROOT, 'cut', 'cut-config.yaml')
GEN_TTS_SCRIPT = os.path.join(GEN_ASSETS_DIR, 'gen_tts.py')


def log(msg):
    print(msg, file=sys.stderr)


def main():
    errors = []

    # -------------------------------------------------------------------------
    # Test 1: Provider files exist
    # -------------------------------------------------------------------------
    log("Test 1: Checking provider files exist...")
    required_files = {
        'tts_base.py': os.path.join(PROVIDERS_DIR, 'tts_base.py'),
        'tts_edge.py': os.path.join(PROVIDERS_DIR, 'tts_edge.py'),
        'tts_openai.py': os.path.join(PROVIDERS_DIR, 'tts_openai.py'),
        'tts_elevenlabs.py': os.path.join(PROVIDERS_DIR, 'tts_elevenlabs.py'),
        'gen_tts.py': GEN_TTS_SCRIPT,
    }
    for name, path in required_files.items():
        if not os.path.exists(path):
            errors.append(f'Missing required file: {path}')
        else:
            # Check it's not a stub (more than 5 lines)
            try:
                with open(path, 'r') as f:
                    lines = [l for l in f.readlines() if l.strip() and not l.strip().startswith('#')]
                if len(lines) <= 3:
                    errors.append(f'{name} appears to be a stub (only {len(lines)} non-comment lines)')
            except Exception as e:
                errors.append(f'Failed to read {name}: {str(e)}')

    # -------------------------------------------------------------------------
    # Test 2: tts_base.py defines a TTSProvider Protocol with synthesize method
    # -------------------------------------------------------------------------
    log("Test 2: Checking tts_base.py defines TTSProvider Protocol...")
    tts_base_path = os.path.join(PROVIDERS_DIR, 'tts_base.py')
    if os.path.exists(tts_base_path):
        try:
            with open(tts_base_path, 'r') as f:
                content = f.read()
            if 'synthesize' not in content:
                errors.append('tts_base.py missing synthesize method definition')
            if 'Protocol' not in content and 'ABC' not in content and 'protocol' not in content.lower():
                errors.append('tts_base.py missing Protocol/ABC abstract base class definition')
        except Exception as e:
            errors.append(f'Failed to read tts_base.py: {str(e)}')

    # -------------------------------------------------------------------------
    # Test 3: gen_tts.py reads cut-config.yaml to select provider
    # -------------------------------------------------------------------------
    log("Test 3: Checking gen_tts.py reads config...")
    if os.path.exists(GEN_TTS_SCRIPT):
        try:
            with open(GEN_TTS_SCRIPT, 'r') as f:
                content = f.read()
            if 'cut-config' not in content and 'config' not in content.lower():
                errors.append('gen_tts.py does not appear to read configuration')
            if 'script.json' not in content and 'script' not in content.lower():
                errors.append('gen_tts.py does not appear to read script.json')
            if 'narration_path' not in content:
                errors.append('gen_tts.py does not update narration_path field in script.json')
        except Exception as e:
            errors.append(f'Failed to read gen_tts.py: {str(e)}')

    # -------------------------------------------------------------------------
    # Test 4: edge_tts provider generates MP3 for Chinese text
    # -------------------------------------------------------------------------
    log("Test 4: Testing edge_tts synthesis with Chinese text...")
    try:
        # Check edge-tts is installed
        result = subprocess.run(
            [sys.executable, '-c', 'import edge_tts; print("ok")'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            errors.append('edge-tts package not installed (pip install edge-tts)')
        else:
            # Try to import and use the edge provider
            sys.path.insert(0, GEN_ASSETS_DIR)
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    output_mp3 = os.path.join(tmpdir, 'test_zh.mp3')
                    # Try importing the provider
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(
                        'tts_edge', os.path.join(PROVIDERS_DIR, 'tts_edge.py')
                    )
                    tts_edge_mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(tts_edge_mod)

                    # Find the provider class
                    provider_class = None
                    for attr_name in dir(tts_edge_mod):
                        attr = getattr(tts_edge_mod, attr_name)
                        if isinstance(attr, type) and attr_name != 'object':
                            if hasattr(attr, 'synthesize'):
                                provider_class = attr
                                break

                    if provider_class is None:
                        errors.append('tts_edge.py does not define a class with synthesize method')
                    else:
                        provider = provider_class()
                        # Run async synthesize using asyncio
                        import asyncio
                        import inspect
                        synthesize_fn = provider.synthesize
                        if asyncio.iscoroutinefunction(synthesize_fn):
                            asyncio.run(synthesize_fn(
                                text='这是中文测试文字，验证普通话合成。',
                                output_path=output_mp3,
                                voice='zh-CN-XiaoxiaoNeural'
                            ))
                        else:
                            synthesize_fn(
                                text='这是中文测试文字，验证普通话合成。',
                                output_path=output_mp3,
                                voice='zh-CN-XiaoxiaoNeural'
                            )

                        if not os.path.exists(output_mp3):
                            errors.append('edge_tts synthesize did not create output MP3 file for Chinese text')
                        elif os.path.getsize(output_mp3) < 1024:
                            errors.append(f'edge_tts output MP3 too small ({os.path.getsize(output_mp3)} bytes), likely empty')
                        else:
                            log(f'  Chinese MP3 created: {os.path.getsize(output_mp3)} bytes')
            except Exception as e:
                errors.append(f'edge_tts Chinese synthesis failed: {str(e)}')
    except subprocess.TimeoutExpired:
        errors.append('Timeout checking edge-tts installation')
    except Exception as e:
        errors.append(f'Test 4 unexpected error: {str(e)}')

    # -------------------------------------------------------------------------
    # Test 5: edge_tts provider generates MP3 for English text
    # -------------------------------------------------------------------------
    log("Test 5: Testing edge_tts synthesis with English text...")
    try:
        sys.path.insert(0, GEN_ASSETS_DIR)
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'tts_edge_en', os.path.join(PROVIDERS_DIR, 'tts_edge.py')
        )
        tts_edge_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tts_edge_mod)

        provider_class = None
        for attr_name in dir(tts_edge_mod):
            attr = getattr(tts_edge_mod, attr_name)
            if isinstance(attr, type) and attr_name != 'object':
                if hasattr(attr, 'synthesize'):
                    provider_class = attr
                    break

        if provider_class is not None:
            with tempfile.TemporaryDirectory() as tmpdir:
                output_mp3 = os.path.join(tmpdir, 'test_en.mp3')
                provider = provider_class()
                import asyncio
                synthesize_fn = provider.synthesize
                if asyncio.iscoroutinefunction(synthesize_fn):
                    asyncio.run(synthesize_fn(
                        text='This is an English test sentence for TTS synthesis.',
                        output_path=output_mp3,
                        voice='en-US-JennyNeural'
                    ))
                else:
                    synthesize_fn(
                        text='This is an English test sentence for TTS synthesis.',
                        output_path=output_mp3,
                        voice='en-US-JennyNeural'
                    )

                if not os.path.exists(output_mp3):
                    errors.append('edge_tts synthesize did not create output MP3 file for English text')
                elif os.path.getsize(output_mp3) < 1024:
                    errors.append(f'edge_tts English MP3 too small ({os.path.getsize(output_mp3)} bytes)')
                else:
                    log(f'  English MP3 created: {os.path.getsize(output_mp3)} bytes')
    except Exception as e:
        errors.append(f'edge_tts English synthesis failed: {str(e)}')

    # -------------------------------------------------------------------------
    # Test 6: gen_tts.py processes 5 scenes and updates script.json narration_path
    # -------------------------------------------------------------------------
    log("Test 6: Testing gen_tts.py processes scenes and updates script.json...")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test workspace
            assets_narration_dir = os.path.join(tmpdir, 'assets', 'narration')
            os.makedirs(assets_narration_dir, exist_ok=True)

            # Create a test script.json with 5 scenes
            test_script = {
                "title": "测试讲稿",
                "total_duration": 50,
                "output_format": "mp4",
                "resolution": "1920x1080",
                "pipeline_state": "draft",
                "scenes": [
                    {
                        "id": f"scene_{i:02d}",
                        "duration": 10,
                        "narration": f"这是第{i}段测试内容，用于验证TTS生成功能。" if i % 2 == 0 else f"This is test scene {i} for TTS generation validation.",
                        "subtitle": f"Scene {i} subtitle",
                        "visual": {
                            "type": "video",
                            "description": f"Scene {i}",
                            "keywords": ["test"],
                            "status": "pending",
                            "selected_candidate": None,
                            "candidates": [],
                            "asset_path": None
                        },
                        "audio": {
                            "narration_status": "pending",
                            "narration_path": None,
                            "music": {
                                "description": "ambient",
                                "keywords": ["mood:calm"],
                                "status": "pending",
                                "selected_candidate": None,
                                "candidates": [],
                                "asset_path": None,
                                "volume": 0.3
                            }
                        }
                    }
                    for i in range(1, 6)
                ]
            }

            script_path = os.path.join(tmpdir, 'script.json')
            with open(script_path, 'w', encoding='utf-8') as f:
                json.dump(test_script, f, ensure_ascii=False, indent=2)

            # Run gen_tts.py with edge_tts provider
            env = os.environ.copy()
            env['TTS_PROVIDER'] = 'edge_tts'  # Allow env override

            result = subprocess.run(
                [sys.executable, GEN_TTS_SCRIPT,
                 '--script', script_path,
                 '--workspace', tmpdir,
                 '--provider', 'edge_tts'],
                capture_output=True, text=True, timeout=120, env=env,
                cwd=PROJECT_ROOT
            )

            log(f"  gen_tts.py stdout: {result.stdout[:500]}")
            log(f"  gen_tts.py stderr: {result.stderr[:500]}")

            if result.returncode != 0:
                errors.append(f'gen_tts.py exited with code {result.returncode}: {result.stderr[:300]}')
            else:
                # Check script.json was updated with narration_path
                try:
                    with open(script_path, 'r', encoding='utf-8') as f:
                        updated_script = json.load(f)

                    filled_count = 0
                    for scene in updated_script.get('scenes', []):
                        narration_path = scene.get('audio', {}).get('narration_path')
                        if narration_path:
                            filled_count += 1
                            # Verify the file actually exists
                            if not os.path.exists(narration_path):
                                errors.append(f"narration_path {narration_path} in script.json does not exist on disk")

                    if filled_count == 0:
                        errors.append('gen_tts.py did not update any audio.narration_path fields in script.json')
                    elif filled_count < 5:
                        errors.append(f'gen_tts.py only filled {filled_count}/5 narration_path fields in script.json')
                    else:
                        log(f'  All {filled_count} narration_path fields filled correctly')

                except Exception as e:
                    errors.append(f'Failed to read updated script.json: {str(e)}')

    except subprocess.TimeoutExpired:
        errors.append('gen_tts.py timed out (>120s) processing 5 scenes')
    except Exception as e:
        errors.append(f'Test 6 unexpected error: {str(e)}')

    # -------------------------------------------------------------------------
    # Test 7: MP3 files are valid and playable (ffprobe check)
    # -------------------------------------------------------------------------
    log("Test 7: Verifying generated MP3 files are playable with ffprobe...")
    try:
        # Check ffprobe is available
        ffprobe_check = subprocess.run(
            ['ffprobe', '-version'],
            capture_output=True, text=True, timeout=5
        )
        if ffprobe_check.returncode != 0:
            errors.append('ffprobe not available — cannot verify MP3 playability')
        else:
            # Generate a sample MP3 and verify with ffprobe
            with tempfile.TemporaryDirectory() as tmpdir:
                output_mp3 = os.path.join(tmpdir, 'ffprobe_test.mp3')
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    'tts_edge_ffprobe', os.path.join(PROVIDERS_DIR, 'tts_edge.py')
                )
                tts_edge_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(tts_edge_mod)

                provider_class = None
                for attr_name in dir(tts_edge_mod):
                    attr = getattr(tts_edge_mod, attr_name)
                    if isinstance(attr, type) and attr_name != 'object':
                        if hasattr(attr, 'synthesize'):
                            provider_class = attr
                            break

                if provider_class is not None:
                    import asyncio
                    provider = provider_class()
                    synthesize_fn = provider.synthesize
                    if asyncio.iscoroutinefunction(synthesize_fn):
                        asyncio.run(synthesize_fn(
                            text='验证音频文件可以正常播放。',
                            output_path=output_mp3,
                            voice='zh-CN-XiaoxiaoNeural'
                        ))
                    else:
                        synthesize_fn(
                            text='验证音频文件可以正常播放。',
                            output_path=output_mp3,
                            voice='zh-CN-XiaoxiaoNeural'
                        )

                    if os.path.exists(output_mp3):
                        ffprobe_result = subprocess.run(
                            ['ffprobe', '-v', 'error', '-show_entries',
                             'format=duration', '-of', 'json', output_mp3],
                            capture_output=True, text=True, timeout=15
                        )
                        if ffprobe_result.returncode != 0:
                            errors.append(f'ffprobe validation failed: {ffprobe_result.stderr[:200]}')
                        else:
                            try:
                                probe_data = json.loads(ffprobe_result.stdout)
                                duration = float(probe_data.get('format', {}).get('duration', 0))
                                if duration <= 0:
                                    errors.append(f'MP3 file has zero duration according to ffprobe')
                                else:
                                    log(f'  ffprobe: MP3 duration = {duration:.2f}s (valid)')
                            except (json.JSONDecodeError, ValueError) as e:
                                errors.append(f'Failed to parse ffprobe output: {str(e)}')
                    else:
                        errors.append('edge_tts did not produce MP3 for ffprobe test')
    except subprocess.TimeoutExpired:
        errors.append('ffprobe check timed out')
    except FileNotFoundError:
        errors.append('ffprobe not found in PATH')
    except Exception as e:
        errors.append(f'Test 7 unexpected error: {str(e)}')

    # -------------------------------------------------------------------------
    # Test 8: OpenAI provider gives clear error when API key is missing
    # -------------------------------------------------------------------------
    log("Test 8: Testing OpenAI provider error message when API key missing...")
    openai_api_key = os.environ.get('OPENAI_API_KEY', '')
    if not openai_api_key:
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                'tts_openai', os.path.join(PROVIDERS_DIR, 'tts_openai.py')
            )
            tts_openai_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(tts_openai_mod)

            provider_class = None
            for attr_name in dir(tts_openai_mod):
                attr = getattr(tts_openai_mod, attr_name)
                if isinstance(attr, type) and attr_name != 'object':
                    if hasattr(attr, 'synthesize'):
                        provider_class = attr
                        break

            if provider_class is None:
                errors.append('tts_openai.py does not define a class with synthesize method')
            else:
                with tempfile.TemporaryDirectory() as tmpdir:
                    output_mp3 = os.path.join(tmpdir, 'openai_test.mp3')
                    # Remove API key from env to simulate missing key
                    env_backup = os.environ.pop('OPENAI_API_KEY', None)
                    try:
                        provider = provider_class()
                        import asyncio
                        synthesize_fn = provider.synthesize
                        try:
                            if asyncio.iscoroutinefunction(synthesize_fn):
                                asyncio.run(synthesize_fn(
                                    text='Test',
                                    output_path=output_mp3,
                                    voice='alloy'
                                ))
                            else:
                                synthesize_fn(text='Test', output_path=output_mp3, voice='alloy')
                            # If it succeeded without a key, that's unexpected but not necessarily wrong
                            # (maybe it raises during init)
                        except Exception as e:
                            err_msg = str(e)
                            # Check it's a user-friendly error, not a raw Python traceback indicator
                            if 'OPENAI_API_KEY' in err_msg or 'api key' in err_msg.lower() or 'api_key' in err_msg.lower():
                                log(f'  OpenAI error message is clear: {err_msg[:100]}')
                            elif 'Traceback' in err_msg or 'AttributeError' in err_msg or 'NoneType' in err_msg:
                                errors.append(f'OpenAI provider exposes raw Python stack trace instead of clear error: {err_msg[:200]}')
                            else:
                                # Accept any error that doesn't look like a raw stack trace
                                log(f'  OpenAI raised error (acceptable): {err_msg[:100]}')
                    finally:
                        if env_backup is not None:
                            os.environ['OPENAI_API_KEY'] = env_backup
        except Exception as e:
            errors.append(f'Test 8 unexpected error: {str(e)}')
    else:
        log(f'  OPENAI_API_KEY is set — testing OpenAI provider with real API...')
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                'tts_openai_live', os.path.join(PROVIDERS_DIR, 'tts_openai.py')
            )
            tts_openai_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(tts_openai_mod)

            provider_class = None
            for attr_name in dir(tts_openai_mod):
                attr = getattr(tts_openai_mod, attr_name)
                if isinstance(attr, type) and attr_name != 'object':
                    if hasattr(attr, 'synthesize'):
                        provider_class = attr
                        break

            if provider_class is None:
                errors.append('tts_openai.py does not define a class with synthesize method')
            else:
                with tempfile.TemporaryDirectory() as tmpdir:
                    output_mp3 = os.path.join(tmpdir, 'openai_live.mp3')
                    provider = provider_class()
                    import asyncio
                    synthesize_fn = provider.synthesize
                    if asyncio.iscoroutinefunction(synthesize_fn):
                        asyncio.run(synthesize_fn(
                            text='Hello, this is OpenAI TTS test.',
                            output_path=output_mp3,
                            voice='alloy'
                        ))
                    else:
                        synthesize_fn(text='Hello, this is OpenAI TTS test.', output_path=output_mp3, voice='alloy')

                    if not os.path.exists(output_mp3):
                        errors.append('OpenAI TTS did not create output MP3 file')
                    elif os.path.getsize(output_mp3) < 1024:
                        errors.append(f'OpenAI TTS MP3 too small ({os.path.getsize(output_mp3)} bytes)')
                    else:
                        log(f'  OpenAI MP3 created: {os.path.getsize(output_mp3)} bytes')
        except Exception as e:
            errors.append(f'OpenAI TTS synthesis failed: {str(e)}')

    # -------------------------------------------------------------------------
    # Test 9: cut-config.yaml has tts.provider = edge_tts (default)
    # -------------------------------------------------------------------------
    log("Test 9: Checking cut-config.yaml has TTS configuration...")
    if not os.path.exists(CUT_CONFIG):
        errors.append(f'cut-config.yaml not found at {CUT_CONFIG}')
    else:
        try:
            import yaml
            with open(CUT_CONFIG, 'r') as f:
                config = yaml.safe_load(f)
            if 'tts' not in config:
                errors.append('cut-config.yaml missing tts section')
            else:
                tts_cfg = config['tts']
                if 'provider' not in tts_cfg:
                    errors.append('cut-config.yaml tts section missing provider field')
                else:
                    log(f'  tts.provider = {tts_cfg["provider"]}')
        except ImportError:
            errors.append('PyYAML not installed (pip install pyyaml)')
        except Exception as e:
            errors.append(f'Failed to parse cut-config.yaml: {str(e)}')

    # -------------------------------------------------------------------------
    # Test 10: SKILL.md documents TTS usage
    # -------------------------------------------------------------------------
    log("Test 10: Checking SKILL.md documents TTS usage...")
    skill_md = os.path.join(PROJECT_ROOT, 'cut', 'skills', 'gen-assets', 'SKILL.md')
    if not os.path.exists(skill_md):
        errors.append(f'SKILL.md not found at {skill_md}')
    else:
        try:
            with open(skill_md, 'r') as f:
                content = f.read()
            if 'tts' not in content.lower() and 'narration' not in content.lower():
                errors.append('SKILL.md does not document TTS/narration usage')
            if len(content.strip()) < 100:
                errors.append(f'SKILL.md is too short ({len(content.strip())} chars), likely not updated for TTS')
        except Exception as e:
            errors.append(f'Failed to read SKILL.md: {str(e)}')

    # -------------------------------------------------------------------------
    # Final result
    # -------------------------------------------------------------------------
    result = {
        'pass': len(errors) == 0,
        'errors': errors
    }

    print(json.dumps(result))
    sys.exit(0 if result['pass'] else 1)


if __name__ == '__main__':
    main()
