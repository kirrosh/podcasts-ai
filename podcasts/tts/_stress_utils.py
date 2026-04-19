"""Shared helpers for TTS providers that consume `+vowel` stress marks."""

from __future__ import annotations

import logging
import re

log = logging.getLogger(__name__)

# Russian vowels (lower + upper). `+` is a stress marker ONLY when the next
# character is a vowel. If `+` sits before a consonant or whitespace, most
# engines (Yandex, F5-TTS) will pronounce it literally as "плюс" or emit an
# artifact. Scrub such stray marks defensively.
_VOWELS = set("аеёиоуыэюяАЕЁИОУЫЭЮЯ")
_BAD_PLUS = re.compile(r"\+([^" + "".join(_VOWELS) + r"])")
_TRAILING_PLUS = re.compile(r"\+(?=\s|$|[^\wа-яА-ЯёЁ])")


def scrub_stray_plus(text: str) -> str:
    """Remove `+` that does not sit before a Russian vowel."""
    before = text.count("+")
    cleaned = _BAD_PLUS.sub(r"\1", text)
    cleaned = _TRAILING_PLUS.sub("", cleaned)
    removed = before - cleaned.count("+")
    if removed:
        log.warning("Scrubbed %d stray '+' marks not before a vowel", removed)
    return cleaned
