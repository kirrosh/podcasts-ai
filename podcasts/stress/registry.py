"""Stress provider registry."""

from __future__ import annotations

from collections.abc import Callable

from podcasts.stress.base import StressProvider


def _ruaccent_factory() -> StressProvider:
    from podcasts.stress.ruaccent import RuAccentStress

    return RuAccentStress()


def _noop_factory() -> StressProvider:
    from podcasts.stress.noop import NoopStress

    return NoopStress()


PROVIDERS: dict[str, Callable[[], StressProvider]] = {
    "ruaccent": _ruaccent_factory,
    "noop": _noop_factory,
}


def get_provider(name: str) -> StressProvider:
    if name not in PROVIDERS:
        available = ", ".join(sorted(PROVIDERS))
        raise KeyError(f"Unknown Stress provider {name!r}. Available: {available}")
    return PROVIDERS[name]()
