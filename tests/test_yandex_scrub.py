"""Tests for Yandex `+` scrubbing logic — does not call the network."""

from podcasts.tts.yandex import YandexTTS


def test_scrub_removes_plus_before_consonant():
    # Misplaced '+' before 'к' (consonant) — Yandex would read it as 'плюс' literally
    assert YandexTTS._scrub_stray_plus("бел+ки") == "белки"


def test_scrub_keeps_valid_stress_marks():
    # Correct Yandex syntax: '+' immediately before the stressed vowel
    # 'з+амок' = stress on first 'а' (castle); 'зам+ок' = stress on 'о' (lock)
    assert YandexTTS._scrub_stray_plus("з+амок и зам+ок") == "з+амок и зам+ок"


def test_scrub_removes_plus_at_word_end():
    assert YandexTTS._scrub_stray_plus("слово+ следующее") == "слово следующее"


def test_scrub_mixed():
    # Both marks are incorrectly placed before consonants
    text = "Я пла+чу налоги и бел+ки прыгают"
    assert YandexTTS._scrub_stray_plus(text) == "Я плачу налоги и белки прыгают"


def test_scrub_preserves_uppercase_before_vowel():
    # '+А' is a correct stress marker (А is a vowel)
    assert YandexTTS._scrub_stray_plus("З+амок") == "З+амок"


def test_scrub_yo_counts_as_vowel():
    # 'ё' is also a stressed vowel
    assert YandexTTS._scrub_stray_plus("кл+ён стоит") == "кл+ён стоит"
