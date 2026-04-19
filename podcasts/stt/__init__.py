"""STT provider abstraction and implementations."""

from podcasts.stt.base import STTProvider
from podcasts.stt.registry import get_provider

__all__ = ["STTProvider", "get_provider"]
