"""Yandex SpeechKit v3 STT provider (sync recognition over gRPC)."""

from __future__ import annotations

import logging
from pathlib import Path

from podcasts.config import ensure_secret, load_secrets

log = logging.getLogger(__name__)


class YandexSTT:
    """Synchronous recognition of short (<1 min) voice messages via SpeechKit v3."""

    name = "yandex"

    def __init__(self) -> None:
        secrets = load_secrets()
        self._api_key = ensure_secret(secrets.yc_api_key, "YC_API_KEY")

    def transcribe(self, audio_path: Path, language: str = "ru-RU") -> str:
        import grpc
        from yandex.cloud.ai.stt.v3 import stt_pb2, stt_service_pb2_grpc

        audio_bytes = audio_path.read_bytes()

        recognize_options = stt_pb2.StreamingOptions(
            recognition_model=stt_pb2.RecognitionModelOptions(
                audio_format=stt_pb2.AudioFormatOptions(
                    container_audio=stt_pb2.ContainerAudio(
                        container_audio_type=stt_pb2.ContainerAudio.OGG_OPUS,
                    ),
                ),
                text_normalization=stt_pb2.TextNormalizationOptions(
                    text_normalization=stt_pb2.TextNormalizationOptions.TEXT_NORMALIZATION_ENABLED,
                    profanity_filter=False,
                    literature_text=True,
                ),
                language_restriction=stt_pb2.LanguageRestrictionOptions(
                    restriction_type=stt_pb2.LanguageRestrictionOptions.WHITELIST,
                    language_code=[language],
                ),
                audio_processing_type=stt_pb2.RecognitionModelOptions.FULL_DATA,
            ),
        )

        def request_generator():
            yield stt_pb2.StreamingRequest(session_options=recognize_options)
            chunk_size = 32 * 1024
            for i in range(0, len(audio_bytes), chunk_size):
                yield stt_pb2.StreamingRequest(
                    chunk=stt_pb2.AudioChunk(data=audio_bytes[i : i + chunk_size])
                )

        credentials = grpc.ssl_channel_credentials()
        text_parts: list[str] = []
        with grpc.secure_channel("stt.api.cloud.yandex.net:443", credentials) as channel:
            stub = stt_service_pb2_grpc.RecognizerStub(channel)
            metadata = (("authorization", f"Api-Key {self._api_key}"),)
            responses = stub.RecognizeStreaming(request_generator(), metadata=metadata)
            for response in responses:
                event_type = response.WhichOneof("Event")
                if event_type == "final":
                    for alt in response.final.alternatives:
                        text_parts.append(alt.text)
                elif event_type == "final_refinement":
                    # refined normalization (punctuation, capitalization)
                    for alt in response.final_refinement.normalized_text.alternatives:
                        # replace the last final chunk with the refined text
                        if text_parts:
                            text_parts[-1] = alt.text
                        else:
                            text_parts.append(alt.text)

        return " ".join(text_parts).strip()
