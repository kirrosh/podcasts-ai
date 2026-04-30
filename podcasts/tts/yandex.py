"""Yandex SpeechKit v3 TTS provider (gRPC)."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from podcasts.config import ensure_secret, load_secrets
from podcasts.tts._stress_utils import scrub_stray_plus

log = logging.getLogger(__name__)

_RETRY_STATUSES = {"UNAVAILABLE", "DEADLINE_EXCEEDED", "INTERNAL", "RESOURCE_EXHAUSTED"}
_MAX_RETRIES = 4
_BASE_BACKOFF_SEC = 1.5

if TYPE_CHECKING:
    from yandex.cloud.ai.tts.v3 import tts_pb2, tts_service_pb2_grpc  # pragma: no cover


# v3 neural voices (as of 2026). marina = female narrator, alena = female warm,
# zahar = male, ermil = male calm, jane = female, omazh = female, madirus = male,
# filipp = male (often cited as highest-quality).
_SUPPORTED_VOICES = ["marina", "alena", "zahar", "ermil", "jane", "omazh", "madirus", "filipp"]


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

        text = scrub_stray_plus(text)

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
        last_err: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                with grpc.secure_channel("tts.api.cloud.yandex.net:443", credentials) as channel:
                    stub = tts_service_pb2_grpc.SynthesizerStub(channel)
                    metadata = (("authorization", f"Api-Key {self._api_key}"),)
                    audio_chunks: list[bytes] = []
                    for response in stub.UtteranceSynthesis(request, metadata=metadata):
                        audio_chunks.append(response.audio_chunk.data)
                    return b"".join(audio_chunks)
            except grpc.RpcError as err:
                last_err = err
                status_name = getattr(err.code(), "name", str(err.code()))
                if status_name not in _RETRY_STATUSES or attempt == _MAX_RETRIES:
                    raise
                backoff = _BASE_BACKOFF_SEC * (2 ** (attempt - 1))
                log.warning(
                    "yandex.tts.retry attempt=%d status=%s sleep=%.1fs",
                    attempt, status_name, backoff,
                )
                time.sleep(backoff)
        assert last_err is not None
        raise last_err

    def supported_voices(self) -> list[str]:
        return list(_SUPPORTED_VOICES)

    def max_chunk_chars(self) -> int:
        # Yandex v3 UtteranceSynthesis hard limit is 250 chars per request
        # (regardless of byte length). Use 230 to leave margin for stress marks.
        return 230

    def output_mime(self) -> str:
        return "audio/ogg"
