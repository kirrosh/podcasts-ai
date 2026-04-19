"""Stress-placement provider protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class StressProvider(Protocol):
    """Places Russian stress marks in text as `+` before the stressed vowel.

    Providers must preserve any `+` marks already present in the input (trust Claude's
    explicit disambiguation for homographs).
    """

    name: str

    def annotate(self, text: str) -> str:
        """Return text with `+` marks before stressed vowels. Input marks preserved."""
        ...
