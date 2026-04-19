"""Tests for sentence-aware chunking."""

from podcasts.util.chunk import chunk_text


def test_empty_text_returns_empty_list():
    assert chunk_text("", 100) == []


def test_short_text_single_chunk():
    text = "Это короткий текст. Меньше лимита."
    chunks = chunk_text(text, 100)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_splits_on_sentence_boundary():
    # Each sentence ~20 chars, limit 40 → 2 sentences per chunk
    text = "Первое предложение. Второе предложение. Третье предложение. Четвёртое предложение."
    chunks = chunk_text(text, 40)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= 40


def test_preserves_stress_marks():
    text = "За+мок стоял на холме. Замо+к висел на воротах."
    chunks = chunk_text(text, 100)
    joined = " ".join(chunks)
    assert "За+мок" in joined
    assert "замо+к" in joined.lower() or "Замо+к" in joined


def test_overlong_sentence_splits_by_words():
    # One sentence longer than limit → must split inside
    text = "Это " + "очень " * 30 + "длинное предложение."
    chunks = chunk_text(text, 40)
    for c in chunks:
        assert len(c) <= 40
