#!/usr/bin/env python3
"""image_sdiffusion.py — Stable Diffusion (Stability AI) image generation provider."""
import os
import base64


class StableDiffusionProvider:
    """Stable Diffusion image generation provider via Stability AI API."""

    def __init__(self, api_key: str = '', engine: str = 'stable-diffusion-xl-1024-v1-0', **kwargs):
        self.api_key = api_key or os.environ.get('STABILITY_API_KEY', '')
        self.engine = engine
        self.api_host = 'https://api.stability.ai'

    def generate(self, prompt: str, output_path: str, size: str = '1024x1024', **kwargs) -> None:
        """Generate an image with Stable Diffusion and save to output_path."""
        if not self.api_key:
            raise ValueError(
                'STABILITY_API_KEY is not set. '
                'Get your key at https://platform.stability.ai/account/keys'
            )

        try:
            import requests
        except ImportError:
            raise ImportError('requests package not installed. Run: pip install requests')

        width, height = (int(x) for x in size.split('x'))
        url = f'{self.api_host}/v1/generation/{self.engine}/text-to-image'
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
        }
        body = {
            'text_prompts': [{'text': prompt, 'weight': 1.0}],
            'cfg_scale': 7,
            'width': width,
            'height': height,
            'samples': 1,
            'steps': 30,
        }
        response = requests.post(url, headers=headers, json=body, timeout=120)
        if response.status_code != 200:
            raise RuntimeError(
                f'Stability AI API error {response.status_code}: {response.text}'
            )
        data = response.json()
        image_b64 = data['artifacts'][0]['base64']
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(base64.b64decode(image_b64))
