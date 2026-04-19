"""STT provider protocol."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class STTProvider(Protocol):
    """Speech-to-text provider contract."""

    name: str

    def transcribe(self, audio_path: Path, language: str = "ru-RU") -> str:
        """Transcribe a local audio file to plain text. Returns stripped text."""
        ...
