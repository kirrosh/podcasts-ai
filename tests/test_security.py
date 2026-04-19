"""Tests for sanitization helpers."""

import pytest

from podcasts.security import enforce_length_cap, sanitize_for_tts


def test_sanitize_strips_control_chars():
    text = "Привет\x00\x01мир"
    assert sanitize_for_tts(text) == "Приветмир"


def test_sanitize_preserves_newlines_and_tabs():
    text = "Строка1\nСтрока2\tТаб"
    result = sanitize_for_tts(text)
    assert "\n" in result
    assert "\t" in result


def test_sanitize_normalizes_unicode():
    # Decomposed form of 'ё' → should become NFC 'ё'
    text = "е\u0308"
    assert sanitize_for_tts(text) == "ё"


def test_sanitize_collapses_excessive_spaces():
    text = "слово     слово"
    assert "   " not in sanitize_for_tts(text)


def test_enforce_length_cap_ok():
    assert enforce_length_cap("короткий текст", max_chars=100) == "короткий текст"


def test_enforce_length_cap_raises():
    long = "x" * 200
    with pytest.raises(ValueError, match="max_script_chars"):
        enforce_length_cap(long, max_chars=100)
