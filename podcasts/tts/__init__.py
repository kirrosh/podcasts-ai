"""TTS provider abstraction and implementations."""

from podcasts.tts.base import TTSProvider
from podcasts.tts.registry import get_provider

__all__ = ["TTSProvider", "get_provider"]
