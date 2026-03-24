#!/usr/bin/env python3
"""image_dalle3.py — DALL-E 3 image generation provider."""
import os
import urllib.request


class Dalle3ImageProvider:
    """DALL-E 3 image generation provider."""

    def __init__(self, api_key: str = '', model: str = 'dall-e-3',
                 quality: str = 'standard', **kwargs):
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY', '')
        self.model = model
        self.quality = quality

    def generate(self, prompt: str, output_path: str, size: str = '1792x1024', **kwargs) -> None:
        """Generate an image with DALL-E 3 and save to output_path."""
        if not self.api_key:
            raise ValueError(
                'OPENAI_API_KEY is not set. '
                'Get your key at https://platform.openai.com/api-keys'
            )

        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                'openai package not installed. Run: pip install openai'
            )

        client = OpenAI(api_key=self.api_key)
        response = client.images.generate(
            model=self.model,
            prompt=prompt,
            size=size,
            quality=self.quality,
            n=1,
        )
        image_url = response.data[0].url
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        urllib.request.urlretrieve(image_url, output_path)
