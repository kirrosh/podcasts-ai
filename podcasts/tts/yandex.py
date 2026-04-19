"""Yandex SpeechKit v3 TTS provider (gRPC)."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from podcasts.config import ensure_secret, load_secrets

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from yandex.cloud.ai.tts.v3 import tts_pb2, tts_service_pb2_grpc  # pragma: no cover


# v3 neural voices (as of 2026). marina = female narrator, alena = female warm,
# zahar = male, ermil = male calm, jane = female, omazh = female, madirus = male,
# filipp = male (often cited as highest-quality).
_SUPPORTED_VOICES = ["marina", "alena", "zahar", "ermil", "jane", "omazh", "madirus", "filipp"]

# Russian vowels (lower + upper). Yandex treats `+` as a stress marker ONLY when
# the next character is a vowel. If `+` sits before a consonant or space, the
# synthesizer pronounces it literally as "плюс". We scrub such stray marks.
_VOWELS = set("аеёиоуыэюяАЕЁИОУЫЭЮЯ")
_BAD_PLUS = re.compile(r"\+([^" + "".join(_VOWELS) + r"])")


class YandexTTS:
    """Yandex SpeechKit v3 synthesizer."""

    name = "yandex"

    def __init__(self) -> None:
        secrets = load_secrets()
        self._api_key = ensure_secret(secrets.yc_api_key, "YC_API_KEY")

    def synthesize(self, text: str, voice: str, speed: float = 1.0) -> bytes:
        """Call SynthesizerService/UtteranceSynthesis, return oggopus bytes."""
        import grpc
        from yandex.cloud.ai.tts.v3 import tts_pb2, tts_service_pb2_grpc  # noqa: F401

        if voice not in _SUPPORTED_VOICES:
            log.warning("Voice %r not in known list %s; trying anyway", voice, _SUPPORTED_VOICES)

        text = self._scrub_stray_plus(text)

        request = tts_pb2.UtteranceSynthesisRequest(
            text=text,
            output_audio_spec=tts_pb2.AudioFormatOptions(
                container_audio=tts_pb2.ContainerAudio(
                    container_audio_type=tts_pb2.ContainerAudio.OGG_OPUS,
                ),
            ),
            hints=[
                tts_pb2.Hints(voice=voice),
                tts_pb2.Hints(speed=speed),
                tts_pb2.Hints(role="neutral"),
            ],
            loudness_normalization_type=tts_pb2.UtteranceSynthesisRequest.LUFS,
        )

        credentials = grpc.ssl_channel_credentials()
        with grpc.secure_channel("tts.api.cloud.yandex.net:443", credentials) as channel:
            stub = tts_service_pb2_grpc.SynthesizerStub(channel)
            metadata = (("authorization", f"Api-Key {self._api_key}"),)
            audio_chunks: list[bytes] = []
            for response in stub.UtteranceSynthesis(request, metadata=metadata):
                audio_chunks.append(response.audio_chunk.data)
            return b"".join(audio_chunks)

    def supported_voices(self) -> list[str]:
        return list(_SUPPORTED_VOICES)

    def max_chunk_chars(self) -> int:
        # Yandex v3 UtteranceSynthesis hard limit is 250 chars per request
        # (regardless of byte length). Use 230 to leave margin for stress marks.
        return 230

    def output_mime(self) -> str:
        return "audio/ogg"

    @staticmethod
    def _scrub_stray_plus(text: str) -> str:
        """Remove `+` that does not sit before a Russian vowel (would be read as 'плюс')."""
        before = text.count("+")
        cleaned = _BAD_PLUS.sub(r"\1", text)
        # Also strip trailing `+` at end of word/string
        cleaned = re.sub(r"\+(?=\s|$|[^\wа-яА-ЯёЁ])", "", cleaned)
        removed = before - cleaned.count("+")
        if removed:
            log.warning("Scrubbed %d stray '+' marks not before a vowel", removed)
        return cleaned
