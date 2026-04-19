"""Transcribe a voice/audio file to text via the configured STT provider.

Usage:
    python -m podcasts.transcribe ~/.claude/channels/telegram/inbox/voice_123.ogg
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from podcasts import stt as stt_mod
from podcasts.config import load_config
from podcasts.util.logging import configure as configure_logging
from podcasts.util.logging import get_logger

log = get_logger(__name__)


def transcribe(audio_path: Path, language: str = "ru-RU") -> str:
    cfg = load_config()
    provider = stt_mod.get_provider(cfg.stt.provider)
    log.info("transcribe.start", audio=str(audio_path), provider=provider.name)
    text = provider.transcribe(audio_path, language=language)
    log.info("transcribe.done", chars=len(text))
    return text


def main() -> int:
    configure_logging()
    parser = argparse.ArgumentParser(description="Transcribe an audio file.")
    parser.add_argument("audio", type=Path, help="Path to audio file (ogg/opus preferred)")
    parser.add_argument("--language", type=str, default="ru-RU")
    args = parser.parse_args()

    if not args.audio.exists():
        print(f"Audio not found: {args.audio}", file=sys.stderr)
        return 1

    text = transcribe(args.audio, language=args.language)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
