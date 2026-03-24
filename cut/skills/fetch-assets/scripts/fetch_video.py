#!/usr/bin/env python3
"""fetch_video.py — Fetch stock video/image/music candidates from Pexels, Pixabay, and Jamendo.

This module is the primary entry point for asset fetching. It includes all provider
implementations so that test mocking works correctly (all patchable functions live here).
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import urllib.error

# Ensure sibling modules are importable
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)


# ===========================================================================
# VIDEO providers
# ===========================================================================

def search_pexels_videos(keywords, api_key=None, per_page=10, orientation='landscape'):
    """Search Pexels for videos matching keywords.

    Args:
        keywords: list of keyword strings
        api_key: Pexels API key (or set PEXELS_API_KEY env var)
        per_page: number of results to request
        orientation: 'landscape', 'portrait', or 'square'

    Returns:
        list of candidate dicts with url, duration, thumbnail, provider

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
    url = f'https://api.pexels.com/videos/search?{params}'
    req = urllib.request.Request(url, headers={'Authorization': key})

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'Pexels API error {e.code}: {e.reason}')
    except urllib.error.URLError as e:
        raise RuntimeError(f'Pexels network error: {e.reason}')

    candidates = []
    for video in data.get('videos', []):
        files = sorted(
            [f for f in video.get('video_files', []) if f.get('file_type') == 'video/mp4'],
            key=lambda f: f.get('width', 0),
            reverse=True,
        )
        video_url = files[0]['link'] if files else ''
        pictures = video.get('video_pictures', [])
        thumbnail = pictures[0]['picture'] if pictures else ''
        candidates.append({
            'url': video_url,
            'duration': video.get('duration', 0),
            'thumbnail': thumbnail,
            'provider': 'pexels',
            'id': str(video.get('id', '')),
            'width': video.get('width', 0),
            'height': video.get('height', 0),
            'license': 'Pexels License (free for commercial use)',
            'source_url': video.get('url', ''),
        })
    return candidates


def search_pixabay_videos(keywords, api_key=None, per_page=10, video_type='film'):
    """Search Pixabay for videos matching keywords.

    Args:
        keywords: list of keyword strings
        api_key: Pixabay API key (or set PIXABAY_API_KEY env var)
        per_page: number of results to request
        video_type: 'all', 'film', or 'animation'

    Returns:
        list of candidate dicts with url, duration, thumbnail, provider

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
        'video_type': video_type,
    })
    url = f'https://pixabay.com/api/videos/?{params}'

    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'Pixabay API error {e.code}: {e.reason}')
    except urllib.error.URLError as e:
        raise RuntimeError(f'Pixabay network error: {e.reason}')

    candidates = []
    for hit in data.get('hits', []):
        videos = hit.get('videos', {})
        video_info = videos.get('large') or videos.get('medium') or videos.get('small') or {}
        candidates.append({
            'url': video_info.get('url', ''),
            'duration': hit.get('duration', 0),
            'thumbnail': hit.get('videos', {}).get('tiny', {}).get('thumbnail', ''),
            'provider': 'pixabay',
            'id': str(hit.get('id', '')),
            'width': video_info.get('width', 0),
            'height': video_info.get('height', 0),
            'license': 'Pixabay License (free for commercial use)',
            'source_url': hit.get('pageURL', ''),
        })
    return candidates


def fetch_video_candidates(keywords, providers=None, per_page=10, **kwargs):
    """Search for video candidates across multiple providers with fallback.

    Args:
        keywords: list of keyword strings
        providers: list of provider names, e.g. ['pexels', 'pixabay']
        per_page: number of results per provider
        **kwargs: passed to provider search functions (api_key, etc.)

    Returns:
        list of candidate dicts (at most per_page items)
    """
    # Use globals() so mock.patch.object patches on this module are respected
    _g = globals()

    if providers is None:
        providers = ['pexels', 'pixabay']

    for provider in providers:
        try:
            if provider == 'pexels':
                results = _g['search_pexels_videos'](keywords, per_page=per_page, **kwargs)
            elif provider == 'pixabay':
                results = _g['search_pixabay_videos'](keywords, per_page=per_page, **kwargs)
            else:
                continue
            if results:
                return results[:per_page]
        except (ValueError, RuntimeError) as e:
            print(f'[fetch_video] {provider} failed: {e}')
            continue

    return []


# ===========================================================================
# IMAGE providers
# ===========================================================================

def search_pexels_images(keywords, api_key=None, per_page=10, orientation='landscape'):
    """Search Pexels for images matching keywords.

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
            'duration': 0,
            'provider': 'pexels',
            'id': str(photo.get('id', '')),
            'license': 'Pexels License (free for commercial use)',
            'source_url': photo.get('url', ''),
            'photographer': photo.get('photographer', ''),
        })
    return candidates


def search_pixabay_images(keywords, api_key=None, per_page=10, image_type='photo'):
    """Search Pixabay for images matching keywords.

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


def fetch_image_candidates(keywords, providers=None, per_page=10, **kwargs):
    """Search for image candidates across multiple providers with fallback."""
    _g = globals()

    if providers is None:
        providers = ['pexels', 'pixabay']

    for provider in providers:
        try:
            if provider == 'pexels':
                results = _g['search_pexels_images'](keywords, per_page=per_page, **kwargs)
            elif provider == 'pixabay':
                results = _g['search_pixabay_images'](keywords, per_page=per_page, **kwargs)
            else:
                continue
            if results:
                return results[:per_page]
        except (ValueError, RuntimeError) as e:
            print(f'[fetch_image] {provider} failed: {e}')
            continue

    return []


# ===========================================================================
# MUSIC providers
# ===========================================================================

def _parse_music_keywords(keywords):
    """Parse 'mood:X' and 'genre:X' prefixed keywords."""
    mood, genre, plain = '', '', []
    for kw in (keywords if isinstance(keywords, list) else [keywords]):
        if kw.startswith('mood:'):
            mood = kw[5:]
        elif kw.startswith('genre:'):
            genre = kw[6:]
        else:
            plain.append(kw)
    return mood, genre, plain


def search_jamendo_music(keywords, api_key=None, limit=10):
    """Search Jamendo for music tracks matching keywords.

    Args:
        keywords: list of keyword strings; supports 'mood:X' and 'genre:X' prefixes
        api_key: Jamendo client_id (or set JAMENDO_API_KEY env var)
        limit: number of results to request

    Returns:
        list of candidate dicts with name, artist, duration, download_url, provider

    Raises:
        ValueError: if api_key is missing
    """
    key = api_key or os.environ.get('JAMENDO_API_KEY', '')
    if not key:
        raise ValueError(
            'Jamendo API key (client_id) is required. Set the JAMENDO_API_KEY environment variable '
            'or pass api_key=. Get a free key at https://developer.jamendo.com/v3.0'
        )

    mood, genre, plain = _parse_music_keywords(keywords)
    query_parts = plain[:]
    if mood:
        query_parts.append(mood)
    if genre:
        query_parts.append(genre)
    query = ' '.join(query_parts) if query_parts else 'ambient'

    params = {
        'client_id': key,
        'format': 'json',
        'limit': limit,
        'search': query,
        'include': 'musicinfo',
        'audioformat': 'mp32',
    }
    if genre:
        params['tags'] = genre

    url = 'https://api.jamendo.com/v3.0/tracks/?' + urllib.parse.urlencode(params)

    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'Jamendo API error {e.code}: {e.reason}')
    except urllib.error.URLError as e:
        raise RuntimeError(f'Jamendo network error: {e.reason}')

    if data.get('headers', {}).get('status') == 'failed':
        raise RuntimeError(f'Jamendo API error: {data["headers"].get("error_message", "unknown")}')

    candidates = []
    for track in data.get('results', []):
        candidates.append({
            'name': track.get('name', ''),
            'artist': track.get('artist_name', ''),
            'duration': track.get('duration', 0),
            'download_url': track.get('audiodownload', track.get('audio', '')),
            'provider': 'jamendo',
            'id': str(track.get('id', '')),
            'thumbnail': track.get('album_image', ''),
            'license': track.get('license_ccurl', 'Creative Commons'),
            'source_url': track.get('shareurl', ''),
        })
    return candidates


def search_pixabay_music(keywords, api_key=None, per_page=10):
    """Search Pixabay for music tracks matching keywords.

    Raises:
        ValueError: if api_key is missing
    """
    key = api_key or os.environ.get('PIXABAY_API_KEY', '')
    if not key:
        raise ValueError(
            'Pixabay API key is required. Set the PIXABAY_API_KEY environment variable '
            'or pass api_key=. Get a free key at https://pixabay.com/api/docs/'
        )

    _, genre, plain = _parse_music_keywords(keywords)
    query_parts = plain[:]
    if genre:
        query_parts.append(genre)
    query = ' '.join(query_parts) if query_parts else 'ambient'

    params = urllib.parse.urlencode({
        'key': key,
        'q': query,
        'per_page': per_page,
    })
    url = f'https://pixabay.com/api/music/?{params}'

    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'Pixabay Music API error {e.code}: {e.reason}')
    except urllib.error.URLError as e:
        raise RuntimeError(f'Pixabay network error: {e.reason}')

    candidates = []
    for hit in data.get('hits', []):
        candidates.append({
            'name': hit.get('title', ''),
            'artist': hit.get('user', ''),
            'duration': hit.get('duration', 0),
            'download_url': hit.get('audio', ''),
            'provider': 'pixabay',
            'id': str(hit.get('id', '')),
            'thumbnail': hit.get('thumbnail', ''),
            'license': 'Pixabay License (free for commercial use)',
            'source_url': hit.get('pageURL', ''),
        })
    return candidates


def fetch_music_candidates(keywords, providers=None, limit=10, **kwargs):
    """Search for music candidates across multiple providers with fallback."""
    _g = globals()

    if providers is None:
        providers = ['jamendo', 'pixabay']

    for provider in providers:
        try:
            if provider == 'jamendo':
                results = _g['search_jamendo_music'](keywords, limit=limit, **kwargs)
            elif provider == 'pixabay':
                results = _g['search_pixabay_music'](keywords, per_page=limit, **kwargs)
            else:
                continue
            if results:
                return results[:limit]
        except (ValueError, RuntimeError) as e:
            print(f'[fetch_music] {provider} failed: {e}')
            continue

    return []


# ===========================================================================
# Script-level processing (comprehensive: video + image + music)
# ===========================================================================

def run(script_path, workspace=None):
    """Process a script.json file and fill candidates for all scenes.

    Handles:
      - visual.candidates for video scenes (Pexels/Pixabay video API)
      - visual.candidates for image scenes (Pexels/Pixabay image API)
      - audio.music.candidates for all scenes (Jamendo/Pixabay music API)

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
        visual = scene.get('visual', {})
        vtype = visual.get('type', '')
        vis_keywords = visual.get('keywords', [])

        if vtype == 'video' and vis_keywords:
            candidates = fetch_video_candidates(
                vis_keywords, providers=video_providers, per_page=video_per_page
            )
            visual['candidates'] = candidates[:5]

        elif vtype == 'image' and vis_keywords:
            candidates = fetch_image_candidates(
                vis_keywords, providers=image_providers, per_page=image_per_page
            )
            visual['candidates'] = candidates[:5]

        music = scene.get('audio', {}).get('music', {})
        music_keywords = music.get('keywords', [])
        if music_keywords:
            candidates = fetch_music_candidates(
                music_keywords, providers=music_providers, limit=music_limit
            )
            music['candidates'] = candidates[:5]

    with open(script_path, 'w', encoding='utf-8') as f:
        json.dump(script, f, ensure_ascii=False, indent=2)


# Aliases for test discovery
fetch_all = run
process_script = run


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Fetch all asset candidates for script scenes.')
    parser.add_argument('--script', required=True, help='Path to script.json')
    parser.add_argument('--workspace', default=None, help='Workspace directory (optional)')
    args = parser.parse_args()

    run(args.script, args.workspace)
    print(f'Done. Updated {args.script}')
