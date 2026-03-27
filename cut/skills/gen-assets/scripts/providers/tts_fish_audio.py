#!/usr/bin/env python3
"""Fish Audio TTS provider for the FFmpeg pipeline (gen_tts.py).

Uses fish-audio-sdk to synthesize speech with voice cloning support.
Requires: pip install fish-audio-sdk
"""

import os


class FishAudioTTSProvider:
    """TTS provider using Fish Audio API with voice cloning.

    Config keys (from cut-config.yaml tts section):
        fish_audio_api_key:    API key (or FISH_AUDIO_API_KEY env var)
        fish_audio_voice_id:   Voice/model reference ID from fish.audio
        fish_audio_model:      Backend model: s2-pro | speech-1.6 | speech-1.5
        fish_audio_mp3_bitrate: 64 | 128 | 192
    """

    def __init__(self, config: dict):
        try:
            from fish_audio_sdk import Session, TTSRequest
            self._Session = Session
            self._TTSRequest = TTSRequest
        except ImportError:
            raise ImportError(
                "fish-audio-sdk not installed. Run: pip install fish-audio-sdk"
            )

        tts_cfg = config.get("tts", {})
        self.api_key = (
            tts_cfg.get("fish_audio_api_key", "")
            or os.environ.get("FISH_AUDIO_API_KEY", "")
        )
        if not self.api_key:
            raise ValueError(
                "Fish Audio API key required. Set fish_audio_api_key in cut-config.yaml "
                "or export FISH_AUDIO_API_KEY=<your-key>"
            )
        self.voice_id = tts_cfg.get("fish_audio_voice_id", "")
        self.model = tts_cfg.get("fish_audio_model", "s2-pro")
        self.mp3_bitrate = tts_cfg.get("fish_audio_mp3_bitrate", 192)

    def synthesize(self, text: str, output_path: str, voice: str = "") -> None:
        """Synthesize text to MP3 file using Fish Audio API."""
        voice_id = voice or self.voice_id
        session = self._Session(self.api_key)
        request = self._TTSRequest(
            text=text,
            reference_id=voice_id if voice_id else None,
            format="mp3",
            mp3_bitrate=self.mp3_bitrate,
            latency="normal",
        )
        audio_bytes = b"".join(session.tts(request, backend=self.model))
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
