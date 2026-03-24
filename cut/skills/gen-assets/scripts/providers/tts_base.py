#!/usr/bin/env python3
"""tts_base.py — Abstract Protocol interface for TTS providers."""
from typing import Protocol, runtime_checkable


@runtime_checkable
class TTSProvider(Protocol):
    """Protocol defining the interface all TTS providers must implement."""

    def synthesize(self, text: str, output_path: str, voice: str) -> None:
        """Synthesize text to speech and save as MP3 to output_path.

        Args:
            text: The text to synthesize.
            output_path: Absolute path where the MP3 file should be saved.
            voice: Voice identifier (provider-specific, e.g. 'zh-CN-XiaoxiaoNeural').

        Raises:
            ValueError: If required API key is missing or configuration is invalid.
            RuntimeError: If synthesis fails for any other reason.
        """
        ...
