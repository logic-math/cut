#!/usr/bin/env python3
"""tts_openai.py — OpenAI TTS provider."""
import os


class OpenAITTSProvider:
    """TTS provider using OpenAI's text-to-speech API."""

    def __init__(self):
        self._api_key = os.environ.get('OPENAI_API_KEY', '')

    def synthesize(self, text: str, output_path: str, voice: str = 'alloy') -> None:
        """Synthesize text to MP3 using OpenAI TTS API.

        Args:
            text: Text to synthesize.
            output_path: Path where the MP3 file will be saved.
            voice: OpenAI voice name ('alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer').

        Raises:
            ValueError: If OPENAI_API_KEY environment variable is not set.
        """
        if not self._api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set. "
                "Please set it with: export OPENAI_API_KEY=your_key_here"
            )

        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError(
                "openai package not installed. Run: pip install openai"
            )

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        client = OpenAI(api_key=self._api_key)
        response = client.audio.speech.create(
            model='tts-1',
            voice=voice,
            input=text,
        )
        response.stream_to_file(output_path)

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError(f"OpenAI TTS produced no output at {output_path}")
