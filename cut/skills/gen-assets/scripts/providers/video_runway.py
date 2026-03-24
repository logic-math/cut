#!/usr/bin/env python3
"""video_runway.py — Runway ML video generation provider with async polling."""
import os
import time
import urllib.request


class RunwayVideoProvider:
    """Runway ML video generation provider."""

    def __init__(self, api_key: str = '', model: str = 'gen3a_turbo', **kwargs):
        self.api_key = api_key or os.environ.get('RUNWAY_API_KEY', '')
        self.model = model
        self.api_base = 'https://api.runwayml.com/v1'
        self.poll_interval = 5
        self.max_wait = 300

    def generate(self, prompt: str, output_path: str, duration: int = 5, **kwargs) -> None:
        """Generate a video with Runway ML and save to output_path."""
        if not self.api_key:
            raise ValueError(
                'RUNWAY_API_KEY is not set. '
                'Get your key at https://app.runwayml.com/settings'
            )

        try:
            import requests
        except ImportError:
            raise ImportError('requests package not installed. Run: pip install requests')

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-Runway-Version': '2024-11-06',
        }

        # Submit generation task
        payload = {
            'promptText': prompt,
            'model': self.model,
            'duration': duration,
            'ratio': '1280:720',
        }
        resp = requests.post(
            f'{self.api_base}/image_to_video',
            headers=headers,
            json=payload,
            timeout=60,
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f'Runway API error {resp.status_code}: {resp.text}'
            )
        task_id = resp.json().get('id')
        if not task_id:
            raise RuntimeError(f'Runway API returned no task id: {resp.text}')

        # Poll for completion
        elapsed = 0
        while elapsed < self.max_wait:
            time.sleep(self.poll_interval)
            elapsed += self.poll_interval
            status_resp = requests.get(
                f'{self.api_base}/tasks/{task_id}',
                headers=headers,
                timeout=30,
            )
            if status_resp.status_code != 200:
                raise RuntimeError(
                    f'Runway status check error {status_resp.status_code}: {status_resp.text}'
                )
            task = status_resp.json()
            status = task.get('status', '')
            if status == 'SUCCEEDED':
                video_url = task.get('output', [None])[0]
                if not video_url:
                    raise RuntimeError('Runway task succeeded but no output URL found')
                os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
                urllib.request.urlretrieve(video_url, output_path)
                return
            elif status in ('FAILED', 'CANCELLED'):
                raise RuntimeError(
                    f'Runway task {task_id} ended with status {status}: '
                    f'{task.get("failure", "")}'
                )

        raise TimeoutError(
            f'Runway task {task_id} did not complete within {self.max_wait}s'
        )
