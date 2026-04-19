"""Tests for SaluteSpeech SSML conversion — no network required."""

from podcasts.tts.salutespeech import _to_ssml


def test_plus_before_vowel_becomes_apostrophe_after():
    # Yandex `з+амок` → Sber `за'мок`
    assert _to_ssml("з+амок") == "<speak>за'мок</speak>"


def test_both_homographs_converted():
    assert _to_ssml("з+амок и зам+ок") == "<speak>за'мок и замо'к</speak>"


def test_uppercase_vowel_preserved():
    assert _to_ssml("З+амок") == "<speak>За'мок</speak>"


def test_yo_is_vowel():
    assert _to_ssml("кл+ён") == "<speak>клё'н</speak>"


def test_xml_special_chars_escaped():
    # `<`, `>`, `&` must be escaped before building SSML
    assert _to_ssml("a & b") == "<speak>a &amp; b</speak>"


def test_speed_wraps_in_paint_tag():
    # Non-default speed uses Sber's <paint> prosody tag
    got = _to_ssml("молок+о", speed=1.2)
    assert got == '<speak><paint speed="1.20">молоко\'</paint></speak>'


def test_no_plus_no_change():
    assert _to_ssml("обычный текст") == "<speak>обычный текст</speak>"
