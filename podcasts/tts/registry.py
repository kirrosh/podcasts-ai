"""TTS provider registry.

To add a new provider:
1. Create `podcasts/tts/<name>.py` implementing the TTSProvider protocol from base.py.
2. If the provider uses a stress-mark syntax different from Yandex's `+vowel`,
   convert inside its .synthesize() method — the orchestrator sends `+`-annotated
   text.
3. Add a factory function and entry to PROVIDERS below.
4. Document the new provider in PROJECT.md and add required env vars to .env.example.
"""

from __future__ import annotations

from collections.abc import Callable

from podcasts.tts.base import TTSProvider


def _yandex_factory() -> TTSProvider:
    from podcasts.tts.yandex import YandexTTS

    return YandexTTS()


PROVIDERS: dict[str, Callable[[], TTSProvider]] = {
    "yandex": _yandex_factory,
}


def get_provider(name: str) -> TTSProvider:
    """Instantiate a TTS provider by name. Raises KeyError with a helpful message."""
    if name not in PROVIDERS:
        available = ", ".join(sorted(PROVIDERS))
        raise KeyError(f"Unknown TTS provider {name!r}. Available: {available}")
    return PROVIDERS[name]()
