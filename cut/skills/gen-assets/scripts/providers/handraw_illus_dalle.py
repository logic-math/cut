#!/usr/bin/env python3
"""handraw_illus_dalle.py — Illustration handraw provider: DALL-E 3 with hand-drawn style prompt."""
import os
import urllib.request

HAND_DRAWN_STYLE_SUFFIX = (
    'hand-drawn illustration, sketch style, black ink on white, rough lines, '
    'pencil drawing, doodle art, educational diagram style'
)


class HandrawIllusDalleProvider:
    """Generates hand-drawn style illustrations using DALL-E 3."""

    def __init__(self, api_key: str = '', model: str = 'dall-e-3',
                 size: str = '1792x1024', quality: str = 'standard', **kwargs):
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY', '')
        self.model = model
        self.size = size
        self.quality = quality

    def generate(self, subject: str, output_path: str, **kwargs) -> str:
        """Generate a hand-drawn illustration and save to output_path."""
        if not self.api_key:
            raise ValueError(
                'OPENAI_API_KEY is not set. '
                'Get your key at https://platform.openai.com/api-keys'
            )

        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError('openai package not installed. Run: pip install openai')

        prompt = f'{subject}, {HAND_DRAWN_STYLE_SUFFIX}'
        client = OpenAI(api_key=self.api_key)
        response = client.images.generate(
            model=self.model,
            prompt=prompt,
            size=self.size,
            quality=self.quality,
            n=1,
        )
        image_url = response.data[0].url
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        urllib.request.urlretrieve(image_url, output_path)
        return output_path


# Module-level convenience function
def generate(subject: str, output_path: str, **kwargs) -> str:
    """Generate a hand-drawn illustration. Convenience wrapper."""
    api_key = kwargs.pop('api_key', '')
    provider = HandrawIllusDalleProvider(api_key=api_key, **kwargs)
    return provider.generate(subject, output_path)
