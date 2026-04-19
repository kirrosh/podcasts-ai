"""Tests for ordered restore of explicit `+` marks — no network / model load."""

from podcasts.stress.ruaccent import RuAccentStress


def test_captures_separate_homograph_variants():
    text = "«Д+ухи прошлого» и дух+и французской марки"
    captured = RuAccentStress._capture_existing_ordered(text)
    assert captured == {"духи": ["Д+ухи", "дух+и"]}


def test_restores_homographs_in_document_order():
    # Simulates: RUAccent dropped original marks and re-guessed homograph
    accented = "«дух+и пр+ошлого» и дух+и фр+анцузской м+арки"
    captured = {"духи": ["Д+ухи", "дух+и"]}
    restored = RuAccentStress._restore_ordered(accented, captured)
    # First "дух+и" → "Д+ухи" (призраки), second stays "дух+и" (парфюм)
    assert restored == "«Д+ухи пр+ошлого» и дух+и фр+анцузской м+арки"


def test_more_words_than_marks_leaves_ruaccent_version():
    accented = "дух+и и дух+и и дух+и"
    captured = {"духи": ["Д+ухи"]}
    restored = RuAccentStress._restore_ordered(accented, captured)
    # Only the first occurrence gets the explicit mark; rest keep RUAccent's guess
    assert restored == "Д+ухи и дух+и и дух+и"


def test_no_explicit_marks_passthrough():
    assert RuAccentStress._restore_ordered("н+етекст", {}) == "н+етекст"


def test_mixed_case_keys_lowercased():
    captured = RuAccentStress._capture_existing_ordered("З+амок и зам+ок")
    # Both keys are lowercased, preserving order
    assert captured == {"замок": ["З+амок", "зам+ок"]}
