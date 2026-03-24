#!/usr/bin/env python3
"""gen_image.py — Generate AI images using configured provider."""
import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, '..', '..', '..', 'cut-config.yaml')

PROVIDER_MAP = {
    'dalle3': None,          # loaded on demand
    'stable_diffusion': None,
}


def _load_config():
    try:
        import yaml
        with open(CONFIG_PATH, 'r') as f:
            return yaml.safe_load(f)
    except Exception:
        return {}


def _get_provider(provider_name: str, api_key: str = '', config: dict = None):
    """Instantiate the image provider by name."""
    config = config or {}
    img_cfg = config.get('image_generation', {})

    if provider_name in ('dalle3', 'dall-e-3', 'dalle_3'):
        from providers.image_dalle3 import Dalle3ImageProvider
        return Dalle3ImageProvider(
            api_key=api_key or os.environ.get('OPENAI_API_KEY', ''),
            model=img_cfg.get('dalle3_model', 'dall-e-3'),
            quality=img_cfg.get('dalle3_quality', 'standard'),
        )
    elif provider_name in ('stable_diffusion', 'sdiffusion', 'stability_ai'):
        from providers.image_sdiffusion import StableDiffusionProvider
        return StableDiffusionProvider(
            api_key=api_key or os.environ.get('STABILITY_API_KEY', ''),
            engine=img_cfg.get('stability_engine', 'stable-diffusion-xl-1024-v1-0'),
        )
    else:
        raise ValueError(
            f'Unknown image provider: {provider_name}. '
            'Supported: dalle3, stable_diffusion'
        )


def generate_image(prompt: str, output_path: str, provider: str = 'dalle3',
                   api_key: str = '', size: str = '1792x1024', **kwargs) -> str:
    """Generate a single image and save to output_path. Returns output_path."""
    config = _load_config()
    img_cfg = config.get('image_generation', {})
    provider_name = provider or img_cfg.get('provider', 'dalle3')
    size = size or img_cfg.get('dalle3_size', '1792x1024')

    prov = _get_provider(provider_name, api_key=api_key, config=config)
    prov.generate(prompt, output_path, size=size)
    return output_path


def run(script_path: str, workspace: str = None, provider: str = None, **kwargs):
    """Process all image-type scenes in script.json and update visual.status."""
    with open(script_path, 'r') as f:
        script = json.load(f)

    config = _load_config()
    img_cfg = config.get('image_generation', {})
    provider_name = provider or img_cfg.get('provider', 'dalle3')
    size = img_cfg.get('dalle3_size', '1792x1024')

    if workspace is None:
        workspace = os.path.dirname(script_path)

    assets_dir = os.path.join(workspace, 'assets', 'images')
    os.makedirs(assets_dir, exist_ok=True)

    prov = _get_provider(provider_name, config=config)
    updated = False

    for scene in script.get('scenes', []):
        visual = scene.get('visual', {})
        if visual.get('type') != 'image':
            continue
        if visual.get('status') == 'ready':
            continue

        scene_id = scene.get('id', 'scene')
        description = visual.get('description', '')
        output_path = os.path.join(assets_dir, f'{scene_id}_image.png')

        try:
            prov.generate(description, output_path, size=size)
            visual['asset_path'] = output_path
            visual['status'] = 'ready'
            updated = True
        except Exception as e:
            visual['status'] = 'error'
            visual['error'] = str(e)
            print(f'[gen_image] Error generating image for {scene_id}: {e}', file=sys.stderr)

    if updated:
        with open(script_path, 'w') as f:
            json.dump(script, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description='Generate AI images for script scenes')
    parser.add_argument('--script', required=True, help='Path to script.json')
    parser.add_argument('--workspace', help='Workspace directory (default: script dir)')
    parser.add_argument('--provider', help='Image provider (dalle3|stable_diffusion)')
    parser.add_argument('--prompt', help='Single prompt mode: generate one image')
    parser.add_argument('--output', help='Output path for single prompt mode')
    args = parser.parse_args()

    if args.prompt and args.output:
        generate_image(args.prompt, args.output, provider=args.provider or 'dalle3')
        print(f'Image saved to: {args.output}')
    else:
        run(args.script, workspace=args.workspace, provider=args.provider)
        print('Image generation complete.')


if __name__ == '__main__':
    sys.path.insert(0, SCRIPT_DIR)
    main()
