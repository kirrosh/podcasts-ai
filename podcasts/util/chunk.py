"""Sentence-aware text chunking up to a character budget."""

from __future__ import annotations

import re

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+(?=[А-ЯA-ZЁ])")


def chunk_text(text: str, max_chars: int) -> list[str]:
    """Split `text` into chunks each <= max_chars, breaking at sentence boundaries.

    Falls back to word boundaries inside overlong sentences.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")

    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    sentences = _SENTENCE_SPLIT.split(text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        s = sentence.strip()
        if not s:
            continue
        sep = 1 if current else 0  # space between sentences
        if current_len + len(s) + sep <= max_chars:
            current.append(s)
            current_len += len(s) + sep
        else:
            if current:
                chunks.append(" ".join(current))
                current = []
                current_len = 0
            if len(s) <= max_chars:
                current.append(s)
                current_len = len(s)
            else:
                # Overlong single sentence: split on words
                chunks.extend(_split_long_sentence(s, max_chars))

    if current:
        chunks.append(" ".join(current))

    return chunks


def _split_long_sentence(sentence: str, max_chars: int) -> list[str]:
    words = sentence.split()
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        sep = 1 if current else 0
        if current_len + len(word) + sep <= max_chars:
            current.append(word)
            current_len += len(word) + sep
        else:
            if current:
                chunks.append(" ".join(current))
            current = [word]
            current_len = len(word)
    if current:
        chunks.append(" ".join(current))
    return chunks
