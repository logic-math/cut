#!/usr/bin/env python3
"""tts_edge.py — edge-tts TTS provider (free, no API key required)."""
import asyncio
import os


class EdgeTTSProvider:
    """TTS provider using Microsoft Edge TTS (via edge-tts package, free)."""

    async def synthesize(self, text: str, output_path: str, voice: str = 'zh-CN-XiaoxiaoNeural') -> None:
        """Synthesize text to MP3 using edge-tts.

        Args:
            text: Text to synthesize.
            output_path: Path where the MP3 file will be saved.
            voice: Edge TTS voice name (e.g. 'zh-CN-XiaoxiaoNeural', 'en-US-JennyNeural').
        """
        try:
            import edge_tts
        except ImportError:
            raise RuntimeError(
                "edge-tts package not installed. Run: pip install edge-tts"
            )

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError(f"edge-tts synthesis produced no output at {output_path}")
