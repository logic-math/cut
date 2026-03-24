#!/usr/bin/env python3
"""fetch_music.py — Fetch stock music candidates from Jamendo and Pixabay."""

import os
import json
import urllib.request
import urllib.parse
import urllib.error


# ---------------------------------------------------------------------------
# Keyword parsing helpers
# ---------------------------------------------------------------------------

def _parse_music_keywords(keywords):
    """Parse music keywords into mood, genre, and plain query terms.

    Supports prefixed keywords like 'mood:calm', 'genre:ambient'.

    Returns:
        (mood, genre, plain_terms) tuple of strings/lists
    """
    mood = ''
    genre = ''
    plain = []
    for kw in (keywords if isinstance(keywords, list) else [keywords]):
        if kw.startswith('mood:'):
            mood = kw[5:]
        elif kw.startswith('genre:'):
            genre = kw[6:]
        else:
            plain.append(kw)
    return mood, genre, plain


# ---------------------------------------------------------------------------
# Provider: Jamendo
# ---------------------------------------------------------------------------

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
    # Build search query: combine plain terms, mood, genre
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
    if mood:
        params['acousticelectronic'] = mood  # best-effort mood mapping

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


# ---------------------------------------------------------------------------
# Provider: Pixabay Music
# ---------------------------------------------------------------------------

def search_pixabay_music(keywords, api_key=None, per_page=10):
    """Search Pixabay for music tracks matching keywords.

    Args:
        keywords: list of keyword strings
        api_key: Pixabay API key (or set PIXABAY_API_KEY env var)
        per_page: number of results to request

    Returns:
        list of candidate dicts with name, artist, duration, download_url, provider

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


# ---------------------------------------------------------------------------
# Multi-provider fallback search
# ---------------------------------------------------------------------------

def fetch_music_candidates(keywords, providers=None, limit=10, **kwargs):
    """Search for music candidates across multiple providers with fallback.

    Args:
        keywords: list of keyword strings (supports 'mood:X', 'genre:X' prefixes)
        providers: list of provider names, e.g. ['jamendo', 'pixabay']
        limit: number of results per provider
        **kwargs: passed to provider search functions (api_key, etc.)

    Returns:
        list of candidate dicts (at most limit items)
    """
    if providers is None:
        providers = ['jamendo', 'pixabay']

    provider_map = {
        'jamendo': lambda kw, **kw2: search_jamendo_music(kw, limit=limit, **kw2),
        'pixabay': lambda kw, **kw2: search_pixabay_music(kw, per_page=limit, **kw2),
    }

    for provider in providers:
        fn = provider_map.get(provider)
        if fn is None:
            continue
        try:
            results = fn(keywords, **kwargs)
            if results:
                return results[:limit]
        except (ValueError, RuntimeError) as e:
            print(f'[fetch_music] {provider} failed: {e}')
            continue

    return []


# ---------------------------------------------------------------------------
# Script-level processing
# ---------------------------------------------------------------------------

def run(script_path, workspace=None):
    """Process a script.json file and fill audio.music.candidates for each scene.

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

    music_cfg = config.get('music', {})
    providers = music_cfg.get('providers', ['jamendo', 'pixabay'])
    limit = music_cfg.get('jamendo_limit', 10)

    for scene in script.get('scenes', []):
        music = scene.get('audio', {}).get('music', {})
        keywords = music.get('keywords', [])
        if not keywords:
            continue

        candidates = fetch_music_candidates(
            keywords,
            providers=providers,
            limit=limit,
        )
        music['candidates'] = candidates[:5]

    with open(script_path, 'w', encoding='utf-8') as f:
        json.dump(script, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Fetch stock music candidates for script scenes.')
    parser.add_argument('--script', required=True, help='Path to script.json')
    parser.add_argument('--workspace', default=None, help='Workspace directory (optional)')
    args = parser.parse_args()

    run(args.script, args.workspace)
    print(f'Done. Updated {args.script}')
