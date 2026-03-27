"""EdgeTTSService — manim-voiceover service using Microsoft edge-tts."""
import asyncio
from pathlib import Path

from manim import logger
from manim_voiceover.helper import remove_bookmarks
from manim_voiceover.services.base import SpeechService

try:
    import edge_tts
except ImportError:
    logger.error('Missing packages. Run `pip install edge-tts` to use EdgeTTSService.')


class EdgeTTSService(SpeechService):
    """SpeechService using Microsoft Edge TTS (free, no API key required).

    Args:
        voice (str): Edge TTS voice name, e.g. 'zh-CN-YunxiNeural'.
            Run `edge-tts --list-voices` to see all options.
        rate (str): Speaking rate, e.g. '+0%', '+10%', '-10%'.
        volume (str): Volume, e.g. '+0%', '+10%'.
    """

    def __init__(self, voice: str = "zh-CN-YunxiNeural", rate: str = "+0%",
                 volume: str = "+0%", **kwargs):
        self.voice = voice
        self.rate = rate
        self.volume = volume
        SpeechService.__init__(self, **kwargs)

    def generate_from_text(
        self, text: str, cache_dir: str = None, path: str = None, **kwargs
    ) -> dict:
        if cache_dir is None:
            cache_dir = self.cache_dir

        input_text = remove_bookmarks(text)
        input_data = {
            "input_text": input_text,
            "service": "edge_tts",
            "voice": self.voice,
            "rate": self.rate,
            "volume": self.volume,
        }

        cached_result = self.get_cached_result(input_data, cache_dir)
        if cached_result is not None:
            return cached_result

        if path is None:
            audio_path = self.get_audio_basename(input_data) + ".mp3"
        else:
            audio_path = path

        output_file = str(Path(cache_dir) / audio_path)

        async def _synthesize():
            communicate = edge_tts.Communicate(
                input_text,
                voice=self.voice,
                rate=self.rate,
                volume=self.volume,
            )
            await communicate.save(output_file)

        try:
            asyncio.run(_synthesize())
        except Exception as e:
            logger.error(f"EdgeTTS synthesis failed: {e}")
            raise

        return {
            "input_text": text,
            "input_data": input_data,
            "original_audio": audio_path,
        }
