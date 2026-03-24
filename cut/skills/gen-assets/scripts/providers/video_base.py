#!/usr/bin/env python3
"""video_base.py — Abstract Protocol interface for video generation providers."""
from typing import Protocol, runtime_checkable


@runtime_checkable
class VideoProvider(Protocol):
    """Protocol for video generation providers."""

    def generate(self, prompt: str, output_path: str, duration: int = 5, **kwargs) -> None:
        """Generate a video clip from a text prompt and save it to output_path."""
        ...
