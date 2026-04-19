"""STT provider registry."""

from __future__ import annotations

from collections.abc import Callable

from podcasts.stt.base import STTProvider


def _yandex_factory() -> STTProvider:
    from podcasts.stt.yandex import YandexSTT

    return YandexSTT()


PROVIDERS: dict[str, Callable[[], STTProvider]] = {
    "yandex": _yandex_factory,
}


def get_provider(name: str) -> STTProvider:
    if name not in PROVIDERS:
        available = ", ".join(sorted(PROVIDERS))
        raise KeyError(f"Unknown STT provider {name!r}. Available: {available}")
    return PROVIDERS[name]()
