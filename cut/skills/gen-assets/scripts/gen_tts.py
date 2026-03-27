#!/usr/bin/env python3
"""gen_tts.py — Generate TTS narration audio for all scenes in script.json."""
import argparse
import asyncio
import inspect
import json
import os
import sys


def load_config(workspace: str) -> dict:
    """Load cut-config.yaml from workspace or fall back to skill default."""
    # Look for config in workspace root, then fall back to skill directory
    config_paths = [
        os.path.join(workspace, 'cut-config.yaml'),
        os.path.join(os.path.dirname(__file__), '..', '..', '..', 'cut-config.yaml'),
    ]
    for path in config_paths:
        path = os.path.abspath(path)
        if os.path.exists(path):
            try:
                import yaml
                with open(path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
    return {}


def get_provider(provider_name: str, config: dict):
    """Instantiate the TTS provider by name."""
    providers_dir = os.path.join(os.path.dirname(__file__), 'providers')
    sys.path.insert(0, os.path.dirname(__file__))

    if provider_name == 'fish_audio':
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'tts_fish_audio', os.path.join(providers_dir, 'tts_fish_audio.py')
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.FishAudioTTSProvider(config)

    elif provider_name == 'edge_tts':
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'tts_edge', os.path.join(providers_dir, 'tts_edge.py')
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.EdgeTTSProvider()

    elif provider_name == 'openai':
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'tts_openai', os.path.join(providers_dir, 'tts_openai.py')
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.OpenAITTSProvider()

    elif provider_name == 'elevenlabs':
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'tts_elevenlabs', os.path.join(providers_dir, 'tts_elevenlabs.py')
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.ElevenLabsTTSProvider()

    else:
        raise ValueError(
            f"Unknown TTS provider: '{provider_name}'. "
            f"Supported: fish_audio, edge_tts, openai, elevenlabs"
        )


def get_voice(provider_name: str, config: dict) -> str:
    """Get the configured voice for the provider."""
    tts_cfg = config.get('tts', {})
    if provider_name == 'fish_audio':
        return tts_cfg.get('fish_audio_voice_id', '')
    elif provider_name == 'edge_tts':
        return tts_cfg.get('voice', 'zh-CN-YunxiNeural')
    elif provider_name == 'openai':
        return tts_cfg.get('openai_voice', 'alloy')
    elif provider_name == 'elevenlabs':
        return tts_cfg.get('elevenlabs_voice_id', 'Rachel')
    return 'zh-CN-YunxiNeural'


def synthesize(provider, text: str, output_path: str, voice: str) -> None:
    """Call provider.synthesize, handling both sync and async implementations."""
    fn = provider.synthesize
    if asyncio.iscoroutinefunction(fn):
        asyncio.run(fn(text=text, output_path=output_path, voice=voice))
    else:
        fn(text=text, output_path=output_path, voice=voice)


def main():
    parser = argparse.ArgumentParser(
        description='Generate TTS narration audio from script.json'
    )
    parser.add_argument('--script', required=True, help='Path to script.json')
    parser.add_argument('--workspace', required=True, help='Project workspace directory')
    parser.add_argument(
        '--provider',
        default=None,
        help='TTS provider override: edge_tts | openai | elevenlabs'
    )
    args = parser.parse_args()

    # Load script.json
    if not os.path.exists(args.script):
        print(f"ERROR: script.json not found at {args.script}", file=sys.stderr)
        sys.exit(1)

    with open(args.script, 'r', encoding='utf-8') as f:
        script = json.load(f)

    # Load config
    config = load_config(args.workspace)

    # Determine provider
    provider_name = args.provider or os.environ.get('TTS_PROVIDER') or \
                    config.get('tts', {}).get('provider', 'edge_tts')

    print(f"Using TTS provider: {provider_name}", file=sys.stderr)

    # Instantiate provider
    try:
        provider = get_provider(provider_name, config)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    voice = get_voice(provider_name, config)

    # Output directory: {workspace}/assets/narration/
    narration_dir = os.path.join(args.workspace, 'assets', 'narration')
    os.makedirs(narration_dir, exist_ok=True)

    scenes = script.get('scenes', [])
    total = len(scenes)
    success_count = 0

    for i, scene in enumerate(scenes):
        scene_id = scene.get('id', f'scene_{i+1:02d}')
        narration_text = scene.get('narration', '').strip()

        if not narration_text:
            print(f"  [{i+1}/{total}] {scene_id}: skipped (empty narration)", file=sys.stderr)
            continue

        output_path = os.path.join(narration_dir, f'{scene_id}.mp3')

        print(f"  [{i+1}/{total}] {scene_id}: synthesizing ({len(narration_text)} chars)...", file=sys.stderr)

        try:
            synthesize(provider, narration_text, output_path, voice)
            # Update script.json in-memory
            if 'audio' not in scene:
                scene['audio'] = {}
            scene['audio']['narration_path'] = output_path
            scene['audio']['narration_status'] = 'done'
            success_count += 1
            print(f"    -> saved to {output_path} ({os.path.getsize(output_path)} bytes)", file=sys.stderr)
        except Exception as e:
            print(f"    ERROR: {e}", file=sys.stderr)
            if 'audio' not in scene:
                scene['audio'] = {}
            scene['audio']['narration_status'] = 'error'

    # Write updated script.json back
    with open(args.script, 'w', encoding='utf-8') as f:
        json.dump(script, f, ensure_ascii=False, indent=2)

    print(f"\nDone: {success_count}/{total} scenes synthesized.", file=sys.stderr)
    if success_count < total:
        sys.exit(1)


if __name__ == '__main__':
    main()
