#!/usr/bin/env python3
"""fetch_assets.py — Unified entry point: fetch all asset candidates for a script.json."""

import os
import sys
import json
import argparse

# Ensure scripts directory is on path for sibling imports
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import fetch_video
import fetch_image
import fetch_music


def fetch_all(script_path, workspace=None):
    """Fetch visual and music candidates for all scenes in script.json.

    Reads script.json, populates:
      - scene.visual.candidates  for video/image scenes
      - scene.audio.music.candidates  for all scenes

    Args:
        script_path: path to script.json
        workspace: optional workspace directory (unused, for API compat)
    """
    with open(script_path, 'r', encoding='utf-8') as f:
        script = json.load(f)

    # Load config
    config = {}
    config_path = os.path.join(_SCRIPTS_DIR, '..', '..', '..', 'cut-config.yaml')
    try:
        import yaml
        with open(config_path, 'r') as cf:
            config = yaml.safe_load(cf) or {}
    except Exception:
        pass

    stock_video_cfg = config.get('stock_video', {})
    stock_image_cfg = config.get('stock_image', {})
    music_cfg = config.get('music', {})

    video_providers = stock_video_cfg.get('providers', ['pexels', 'pixabay'])
    image_providers = stock_image_cfg.get('providers', ['pexels', 'pixabay'])
    music_providers = music_cfg.get('providers', ['jamendo', 'pixabay'])
    video_per_page = stock_video_cfg.get('pexels_per_page', 10)
    image_per_page = stock_image_cfg.get('pexels_per_page', 10)
    music_limit = music_cfg.get('jamendo_limit', 10)

    for scene in script.get('scenes', []):
        sid = scene.get('id', '?')
        visual = scene.get('visual', {})
        vtype = visual.get('type', '')
        vis_keywords = visual.get('keywords', [])

        # Fetch visual candidates
        if vtype == 'video' and vis_keywords:
            print(f'  [video] scene {sid}: {vis_keywords}')
            candidates = fetch_video.fetch_video_candidates(
                vis_keywords, providers=video_providers, per_page=video_per_page
            )
            visual['candidates'] = candidates[:5]

        elif vtype == 'image' and vis_keywords:
            print(f'  [image] scene {sid}: {vis_keywords}')
            candidates = fetch_image.fetch_image_candidates(
                vis_keywords, providers=image_providers, per_page=image_per_page
            )
            visual['candidates'] = candidates[:5]

        # Fetch music candidates
        music = scene.get('audio', {}).get('music', {})
        music_keywords = music.get('keywords', [])
        if music_keywords:
            print(f'  [music] scene {sid}: {music_keywords}')
            candidates = fetch_music.fetch_music_candidates(
                music_keywords, providers=music_providers, limit=music_limit
            )
            music['candidates'] = candidates[:5]

    with open(script_path, 'w', encoding='utf-8') as f:
        json.dump(script, f, ensure_ascii=False, indent=2)

    print(f'Done. Candidates written to {script_path}')


# Alias for test discovery
run = fetch_all
process_script = fetch_all


def main():
    parser = argparse.ArgumentParser(
        description='Fetch all asset candidates (video, image, music) for a script.json.'
    )
    parser.add_argument('--script', required=True, help='Path to script.json')
    parser.add_argument('--workspace', default=None, help='Workspace directory (optional)')
    args = parser.parse_args()

    fetch_all(args.script, args.workspace)


if __name__ == '__main__':
    main()
