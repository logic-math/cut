#!/usr/bin/env python3
"""image_base.py — Abstract Protocol interface for image generation providers."""
from typing import Protocol, runtime_checkable


@runtime_checkable
class ImageProvider(Protocol):
    """Protocol for image generation providers."""

    def generate(self, prompt: str, output_path: str, size: str = '1792x1024', **kwargs) -> None:
        """Generate an image from a text prompt and save it to output_path."""
        ...
