"""TTS provider protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TTSProvider(Protocol):
    """Text-to-speech provider contract.

    Providers accept already-stress-annotated Russian text and return audio bytes.
    The orchestrator does not normalize voice names — the caller must pass a
    voice supported by the selected provider.
    """

    name: str

    def synthesize(self, text: str, voice: str, speed: float = 1.0) -> bytes:
        """Synthesize a single chunk. Returns raw audio bytes in `output_mime()` format."""
        ...

    def supported_voices(self) -> list[str]:
        """List voices this provider supports. Used for validation and CLI help."""
        ...

    def max_chunk_chars(self) -> int:
        """Hard upper bound on text length per synthesize() call. Orchestrator chunks below this."""
        ...

    def output_mime(self) -> str:
        """Mime type of synthesized bytes, e.g. 'audio/ogg' or 'audio/mpeg'."""
        ...
