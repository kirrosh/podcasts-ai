"""Tests for provider registries — lazy loading and error messages."""

import pytest

from podcasts.stress.registry import get_provider as get_stress
from podcasts.stt.registry import get_provider as get_stt
from podcasts.tts.registry import get_provider as get_tts


def test_stress_noop_instantiates_without_deps():
    provider = get_stress("noop")
    assert provider.name == "noop"
    assert provider.annotate("тест") == "тест"


def test_unknown_stress_provider_raises():
    with pytest.raises(KeyError, match="Unknown Stress provider"):
        get_stress("nonexistent")


def test_unknown_tts_provider_raises():
    with pytest.raises(KeyError, match="Unknown TTS provider"):
        get_tts("nonexistent")


def test_unknown_stt_provider_raises():
    with pytest.raises(KeyError, match="Unknown STT provider"):
        get_stt("nonexistent")
