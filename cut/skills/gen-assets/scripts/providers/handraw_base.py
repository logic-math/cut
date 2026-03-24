#!/usr/bin/env python3
"""handraw_base.py — Abstract Protocol interface for handraw visual providers."""
from typing import Protocol, runtime_checkable


@runtime_checkable
class HandrawProvider(Protocol):
    """Protocol for handraw (hand-drawn visual) generation providers."""

    def generate(self, subject: str, output_path: str, **kwargs) -> str:
        """Generate a handraw visual from a subject description and save to output_path.

        Returns the output_path on success.
        """
        ...
