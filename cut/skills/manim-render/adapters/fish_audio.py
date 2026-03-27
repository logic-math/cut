"""FishAudioService — manim-voiceover service using Fish Audio TTS API.

Supports Fish Audio's voice cloning models including S2 Pro (highest quality).

Requirements:
    pip install fish-audio-sdk

Config (cut-config.yaml):
    tts:
      provider: fish_audio
      fish_audio_api_key: "your-api-key"        # or set FISH_AUDIO_API_KEY env var
      fish_audio_voice_id: "your-voice-model-id" # voice/model ID from fish.audio
      fish_audio_model: "s2-pro"                 # s2-pro | speech-1.6 | speech-1.5
"""

import os
from pathlib import Path

from manim import logger
from manim_voiceover.helper import remove_bookmarks
from manim_voiceover.services.base import SpeechService

try:
    from fish_audio_sdk import Session, TTSRequest
    HAS_FISH_AUDIO = True
except ImportError:
    HAS_FISH_AUDIO = False


class FishAudioService(SpeechService):
    """SpeechService using Fish Audio TTS API.

    Args:
        api_key (str): Fish Audio API key. Falls back to FISH_AUDIO_API_KEY env var.
        voice_id (str): Voice/model reference ID from fish.audio.
        model (str): Backend model. Options: 's2-pro', 'speech-1.6', 'speech-1.5'.
                     Defaults to 's2-pro' (highest quality).
        mp3_bitrate (int): MP3 bitrate. Options: 64, 128, 192. Defaults to 192.
        latency (str): 'normal' or 'balanced'. Defaults to 'normal'.
    """

    def __init__(
        self,
        api_key: str = "",
        voice_id: str = "",
        model: str = "s2-pro",
        mp3_bitrate: int = 192,
        latency: str = "normal",
        **kwargs,
    ):
        if not HAS_FISH_AUDIO:
            raise ImportError('Missing fish-audio-sdk. Run `pip install fish-audio-sdk`.')

        self.api_key = api_key or os.environ.get("FISH_AUDIO_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "Fish Audio API key required. Pass api_key= or set FISH_AUDIO_API_KEY env var."
            )

        self.voice_id = voice_id
        self.model = model
        self.mp3_bitrate = mp3_bitrate
        self.latency = latency

        SpeechService.__init__(self, **kwargs)

    def generate_from_text(
        self, text: str, cache_dir: str = None, path: str = None, **kwargs
    ) -> dict:
        if cache_dir is None:
            cache_dir = self.cache_dir

        input_text = remove_bookmarks(text)
        input_data = {
            "input_text": input_text,
            "service": "fish_audio",
            "voice_id": self.voice_id,
            "model": self.model,
            "mp3_bitrate": self.mp3_bitrate,
        }

        cached_result = self.get_cached_result(input_data, cache_dir)
        if cached_result is not None:
            return cached_result

        if path is None:
            audio_path = self.get_audio_basename(input_data) + ".mp3"
        else:
            audio_path = path

        output_file = Path(cache_dir) / audio_path

        try:
            session = Session(self.api_key)
            request = TTSRequest(
                text=input_text,
                reference_id=self.voice_id if self.voice_id else None,
                format="mp3",
                mp3_bitrate=self.mp3_bitrate,
                latency=self.latency,
            )

            audio_bytes = b"".join(session.tts(request, backend=self.model))

            with open(output_file, "wb") as f:
                f.write(audio_bytes)

            logger.info(f"FishAudio TTS: {len(audio_bytes)} bytes → {audio_path}")

        except Exception as e:
            logger.error(f"FishAudio TTS failed: {e}")
            raise

        return {
            "input_text": text,
            "input_data": input_data,
            "original_audio": audio_path,
        }
