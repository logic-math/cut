#!/usr/bin/env python3
"""gen_handraw.py — Entry point for handraw asset generation; routes to chart or illustration provider."""
import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, '..', '..', '..', 'cut-config.yaml')

# Provider map: handraw_type -> provider class (loaded on demand)
# Add new providers here without modifying the rest of this file.
provider_map = {
    'handraw_chart': 'providers.handraw_chart_svg:HandrawChartSVGProvider',
    'handraw_illustration': 'providers.handraw_illus_dalle:HandrawIllusDalleProvider',
}


def _load_config():
    try:
        import yaml
        with open(CONFIG_PATH, 'r') as f:
            return yaml.safe_load(f)
    except Exception:
        return {}


def _import_provider_class(dotted_path: str):
    """Import a provider class from 'module:ClassName' string."""
    module_path, cls_name = dotted_path.rsplit(':', 1)
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, cls_name)


def get_provider(handraw_type: str, config: dict = None, api_key: str = ''):
    """Return an instantiated provider for the given handraw_type."""
    config = config or {}
    hw_cfg = config.get('handraw', {})

    if handraw_type not in provider_map:
        raise ValueError(
            f'Unknown handraw_type: {handraw_type}. '
            f'Supported: {list(provider_map.keys())}'
        )

    cls_path = provider_map[handraw_type]
    if isinstance(cls_path, str):
        cls = _import_provider_class(cls_path)
    else:
        cls = cls_path  # already a class (e.g. injected for testing)

    if handraw_type == 'handraw_chart':
        return cls(dpi=hw_cfg.get('chart_dpi', 150))
    elif handraw_type == 'handraw_illustration':
        return cls(
            api_key=api_key or os.environ.get('OPENAI_API_KEY', ''),
            size=hw_cfg.get('illustration_size', '1792x1024'),
        )
    else:
        return cls()


def generate(subject: str, output_path: str, handraw_type: str = 'handraw_chart',
             provider=None, api_key: str = '', **kwargs) -> str:
    """Generate a handraw visual and save to output_path.

    Args:
        subject: Description of what to draw.
        output_path: Where to save the output PNG.
        handraw_type: 'handraw_chart' or 'handraw_illustration' (or custom via provider_map).
        provider: Optional pre-instantiated provider (for testing/injection).
        api_key: API key override.

    Returns:
        output_path on success.
    """
    if provider is None:
        config = _load_config()
        provider = get_provider(handraw_type, config=config, api_key=api_key)
    return provider.generate(subject, output_path, **kwargs)


def run(script_path: str, workspace: str = None, **kwargs):
    """Process all handraw-type scenes in script.json and update visual.status."""
    with open(script_path, 'r') as f:
        script = json.load(f)

    config = _load_config()
    if workspace is None:
        workspace = os.path.dirname(script_path)

    assets_dir = os.path.join(workspace, 'assets', 'handraw')
    os.makedirs(assets_dir, exist_ok=True)

    updated = False
    for scene in script.get('scenes', []):
        visual = scene.get('visual', {})
        vtype = visual.get('type', '')
        if vtype not in ('handraw_chart', 'handraw_illustration'):
            continue
        if visual.get('status') == 'ready':
            continue

        scene_id = scene.get('id', 'scene')
        description = visual.get('description', '')
        output_path = os.path.join(assets_dir, f'{scene_id}_handraw.png')

        try:
            prov = get_provider(vtype, config=config)
            prov.generate(description, output_path)
            visual['asset_path'] = output_path
            visual['status'] = 'ready'
            updated = True
        except Exception as e:
            visual['status'] = 'error'
            visual['error'] = str(e)
            print(f'[gen_handraw] Error generating {vtype} for {scene_id}: {e}', file=sys.stderr)

    if updated:
        with open(script_path, 'w') as f:
            json.dump(script, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description='Generate handraw visuals for script scenes')
    parser.add_argument('--script', required=True, help='Path to script.json')
    parser.add_argument('--workspace', help='Workspace directory (default: script dir)')
    parser.add_argument('--subject', help='Single subject mode: generate one handraw')
    parser.add_argument('--output', help='Output path for single subject mode')
    parser.add_argument('--type', dest='handraw_type', default='handraw_chart',
                        help='handraw_type: handraw_chart | handraw_illustration')
    args = parser.parse_args()

    if args.subject and args.output:
        result = generate(args.subject, args.output, handraw_type=args.handraw_type)
        print(f'Handraw saved to: {result}')
    else:
        run(args.script, workspace=args.workspace)
        print('Handraw generation complete.')


if __name__ == '__main__':
    sys.path.insert(0, SCRIPT_DIR)
    main()
