#!/usr/bin/env python3
"""gen_video.py — Generate AI video clips using configured provider."""
import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, '..', '..', '..', 'cut-config.yaml')


def _load_config():
    try:
        import yaml
        with open(CONFIG_PATH, 'r') as f:
            return yaml.safe_load(f)
    except Exception:
        return {}


def _get_provider(provider_name: str, api_key: str = '', config: dict = None):
    """Instantiate the video provider by name."""
    config = config or {}
    vid_cfg = config.get('video_generation', {})

    if provider_name in ('runway', 'runwayml', 'runway_ml'):
        from providers.video_runway import RunwayVideoProvider
        return RunwayVideoProvider(
            api_key=api_key or os.environ.get('RUNWAY_API_KEY', ''),
            model=vid_cfg.get('runway_model', 'gen3a_turbo'),
        )
    else:
        raise ValueError(
            f'Unknown video provider: {provider_name}. '
            'Supported: runway'
        )


def generate_video(prompt: str, output_path: str, provider: str = 'runway',
                   duration: int = 5, api_key: str = '', **kwargs) -> str:
    """Generate a single video clip and save to output_path. Returns output_path."""
    config = _load_config()
    vid_cfg = config.get('video_generation', {})
    provider_name = provider or vid_cfg.get('provider', 'runway')
    duration = duration or vid_cfg.get('runway_duration', 5)

    prov = _get_provider(provider_name, api_key=api_key, config=config)
    prov.generate(prompt, output_path, duration=duration)
    return output_path


def run(script_path: str, workspace: str = None, provider: str = None, **kwargs):
    """Process all video-type scenes in script.json and update visual.status."""
    with open(script_path, 'r') as f:
        script = json.load(f)

    config = _load_config()
    vid_cfg = config.get('video_generation', {})
    provider_name = provider or vid_cfg.get('provider', 'runway')
    duration = vid_cfg.get('runway_duration', 5)

    if workspace is None:
        workspace = os.path.dirname(script_path)

    assets_dir = os.path.join(workspace, 'assets', 'videos')
    os.makedirs(assets_dir, exist_ok=True)

    prov = _get_provider(provider_name, config=config)
    updated = False

    for scene in script.get('scenes', []):
        visual = scene.get('visual', {})
        if visual.get('type') != 'video':
            continue
        if visual.get('status') == 'ready':
            continue

        scene_id = scene.get('id', 'scene')
        description = visual.get('description', '')
        output_path = os.path.join(assets_dir, f'{scene_id}_video.mp4')

        try:
            prov.generate(description, output_path, duration=duration)
            visual['asset_path'] = output_path
            visual['status'] = 'ready'
            updated = True
        except Exception as e:
            visual['status'] = 'error'
            visual['error'] = str(e)
            print(f'[gen_video] Error generating video for {scene_id}: {e}', file=sys.stderr)

    if updated:
        with open(script_path, 'w') as f:
            json.dump(script, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description='Generate AI video clips for script scenes')
    parser.add_argument('--script', required=True, help='Path to script.json')
    parser.add_argument('--workspace', help='Workspace directory (default: script dir)')
    parser.add_argument('--provider', help='Video provider (runway)')
    parser.add_argument('--prompt', help='Single prompt mode: generate one video')
    parser.add_argument('--output', help='Output path for single prompt mode')
    parser.add_argument('--duration', type=int, default=5, help='Video duration in seconds')
    args = parser.parse_args()

    if args.prompt and args.output:
        generate_video(args.prompt, args.output, provider=args.provider or 'runway',
                       duration=args.duration)
        print(f'Video saved to: {args.output}')
    else:
        run(args.script, workspace=args.workspace, provider=args.provider)
        print('Video generation complete.')


if __name__ == '__main__':
    sys.path.insert(0, SCRIPT_DIR)
    main()
