#!/usr/bin/env python3
"""fetch_image.py — Fetch stock image candidates from Pexels and Pixabay."""

import os
import json
import urllib.request
import urllib.parse
import urllib.error


# ---------------------------------------------------------------------------
# Provider: Pexels
# ---------------------------------------------------------------------------

def search_pexels_images(keywords, api_key=None, per_page=10, orientation='landscape'):
    """Search Pexels for images matching keywords.

    Args:
        keywords: list of keyword strings
        api_key: Pexels API key (or set PEXELS_API_KEY env var)
        per_page: number of results to request
        orientation: 'landscape', 'portrait', or 'square'

    Returns:
        list of candidate dicts with url, thumbnail, width, height, provider

    Raises:
        ValueError: if api_key is missing
    """
    key = api_key or os.environ.get('PEXELS_API_KEY', '')
    if not key:
        raise ValueError(
            'Pexels API key is required. Set the PEXELS_API_KEY environment variable '
            'or pass api_key=. Get a free key at https://www.pexels.com/api/'
        )

    query = ' '.join(keywords) if isinstance(keywords, list) else keywords
    params = urllib.parse.urlencode({
        'query': query,
        'per_page': per_page,
        'orientation': orientation,
    })
    url = f'https://api.pexels.com/v1/search?{params}'
    req = urllib.request.Request(url, headers={'Authorization': key})

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'Pexels API error {e.code}: {e.reason}')
    except urllib.error.URLError as e:
        raise RuntimeError(f'Pexels network error: {e.reason}')

    candidates = []
    for photo in data.get('photos', []):
        src = photo.get('src', {})
        candidates.append({
            'url': src.get('original', ''),
            'thumbnail': src.get('medium', src.get('small', '')),
            'width': photo.get('width', 0),
            'height': photo.get('height', 0),
            'duration': 0,  # images have no duration
            'provider': 'pexels',
            'id': str(photo.get('id', '')),
            'license': 'Pexels License (free for commercial use)',
            'source_url': photo.get('url', ''),
            'photographer': photo.get('photographer', ''),
        })
    return candidates


# ---------------------------------------------------------------------------
# Provider: Pixabay
# ---------------------------------------------------------------------------

def search_pixabay_images(keywords, api_key=None, per_page=10, image_type='photo'):
    """Search Pixabay for images matching keywords.

    Args:
        keywords: list of keyword strings
        api_key: Pixabay API key (or set PIXABAY_API_KEY env var)
        per_page: number of results to request
        image_type: 'all', 'photo', 'illustration', or 'vector'

    Returns:
        list of candidate dicts with url, thumbnail, width, height, provider

    Raises:
        ValueError: if api_key is missing
    """
    key = api_key or os.environ.get('PIXABAY_API_KEY', '')
    if not key:
        raise ValueError(
            'Pixabay API key is required. Set the PIXABAY_API_KEY environment variable '
            'or pass api_key=. Get a free key at https://pixabay.com/api/docs/'
        )

    query = ' '.join(keywords) if isinstance(keywords, list) else keywords
    params = urllib.parse.urlencode({
        'key': key,
        'q': query,
        'per_page': per_page,
        'image_type': image_type,
        'orientation': 'horizontal',
    })
    url = f'https://pixabay.com/api/?{params}'

    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'Pixabay API error {e.code}: {e.reason}')
    except urllib.error.URLError as e:
        raise RuntimeError(f'Pixabay network error: {e.reason}')

    candidates = []
    for hit in data.get('hits', []):
        candidates.append({
            'url': hit.get('largeImageURL', hit.get('webformatURL', '')),
            'thumbnail': hit.get('previewURL', ''),
            'width': hit.get('imageWidth', 0),
            'height': hit.get('imageHeight', 0),
            'duration': 0,
            'provider': 'pixabay',
            'id': str(hit.get('id', '')),
            'license': 'Pixabay License (free for commercial use)',
            'source_url': hit.get('pageURL', ''),
            'photographer': hit.get('user', ''),
        })
    return candidates


# ---------------------------------------------------------------------------
# Multi-provider fallback search
# ---------------------------------------------------------------------------

def fetch_image_candidates(keywords, providers=None, per_page=10, **kwargs):
    """Search for image candidates across multiple providers with fallback.

    Args:
        keywords: list of keyword strings
        providers: list of provider names, e.g. ['pexels', 'pixabay']
        per_page: number of results per provider
        **kwargs: passed to provider search functions (api_key, etc.)

    Returns:
        list of candidate dicts (at most per_page items)
    """
    if providers is None:
        providers = ['pexels', 'pixabay']

    provider_map = {
        'pexels': search_pexels_images,
        'pixabay': search_pixabay_images,
    }

    for provider in providers:
        fn = provider_map.get(provider)
        if fn is None:
            continue
        try:
            results = fn(keywords, per_page=per_page, **kwargs)
            if results:
                return results[:per_page]
        except (ValueError, RuntimeError) as e:
            print(f'[fetch_image] {provider} failed: {e}')
            continue

    return []


# ---------------------------------------------------------------------------
# Script-level processing
# ---------------------------------------------------------------------------

def run(script_path, workspace=None):
    """Process a script.json file and fill visual.candidates for image scenes.

    Args:
        script_path: path to script.json
        workspace: optional workspace directory (unused, for API compat)
    """
    with open(script_path, 'r', encoding='utf-8') as f:
        script = json.load(f)

    config = {}
    config_path = os.path.join(
        os.path.dirname(__file__), '..', '..', '..', 'cut-config.yaml'
    )
    try:
        import yaml
        with open(config_path, 'r') as cf:
            config = yaml.safe_load(cf) or {}
    except Exception:
        pass

    stock_cfg = config.get('stock_image', {})
    providers = stock_cfg.get('providers', ['pexels', 'pixabay'])
    per_page = stock_cfg.get('pexels_per_page', 10)

    for scene in script.get('scenes', []):
        visual = scene.get('visual', {})
        vtype = visual.get('type', '')
        if vtype not in ('image',):
            continue
        keywords = visual.get('keywords', [])
        if not keywords:
            continue

        candidates = fetch_image_candidates(
            keywords,
            providers=providers,
            per_page=per_page,
        )
        visual['candidates'] = candidates[:5]

    with open(script_path, 'w', encoding='utf-8') as f:
        json.dump(script, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Fetch stock image candidates for script scenes.')
    parser.add_argument('--script', required=True, help='Path to script.json')
    parser.add_argument('--workspace', default=None, help='Workspace directory (optional)')
    args = parser.parse_args()

    run(args.script, args.workspace)
    print(f'Done. Updated {args.script}')
