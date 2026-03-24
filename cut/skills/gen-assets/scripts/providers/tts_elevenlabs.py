#!/usr/bin/env python3
"""tts_elevenlabs.py — ElevenLabs TTS provider."""
import os


class ElevenLabsTTSProvider:
    """TTS provider using ElevenLabs text-to-speech API."""

    def __init__(self):
        self._api_key = os.environ.get('ELEVENLABS_API_KEY', '')

    def synthesize(self, text: str, output_path: str, voice: str = 'Rachel') -> None:
        """Synthesize text to MP3 using ElevenLabs TTS API.

        Args:
            text: Text to synthesize.
            output_path: Path where the MP3 file will be saved.
            voice: ElevenLabs voice ID or name (e.g. 'Rachel', '21m00Tcm4TlvDq8ikWAM').

        Raises:
            ValueError: If ELEVENLABS_API_KEY environment variable is not set.
        """
        if not self._api_key:
            raise ValueError(
                "ELEVENLABS_API_KEY environment variable is not set. "
                "Please set it with: export ELEVENLABS_API_KEY=your_key_here"
            )

        try:
            from elevenlabs.client import ElevenLabs
            from elevenlabs import save
        except ImportError:
            raise RuntimeError(
                "elevenlabs package not installed. Run: pip install elevenlabs"
            )

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        client = ElevenLabs(api_key=self._api_key)
        audio = client.generate(text=text, voice=voice, model='eleven_multilingual_v2')
        save(audio, output_path)

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError(f"ElevenLabs TTS produced no output at {output_path}")
