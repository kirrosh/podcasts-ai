"""Script (.txt) → stress-annotated → TTS chunks → single mp3.

Usage:
    python -m podcasts.build scripts/2026-04-19-kapital-01.txt
    python -m podcasts.build scripts/x.txt --voice alena --style fireside --out audio/x.mp3
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

from pydub import AudioSegment

from podcasts import stress as stress_mod
from podcasts import tts as tts_mod
from podcasts.config import PROJECT_ROOT, load_config
from podcasts.security import check_rate_limit, enforce_length_cap, sanitize_for_tts
from podcasts.util.chunk import chunk_text
from podcasts.util.logging import configure as configure_logging
from podcasts.util.logging import get_logger

log = get_logger(__name__)


def build(
    script_path: Path,
    out_path: Path | None = None,
    voice: str | None = None,
    speed: float | None = None,
) -> Path:
    """Read a script, annotate stress, synthesize, stitch, write mp3. Returns output path."""
    cfg = load_config()
    effective_voice = voice or cfg.tts.voice
    effective_speed = speed if speed is not None else cfg.tts.speed

    raw_text = script_path.read_text(encoding="utf-8")
    text = sanitize_for_tts(raw_text)
    text = enforce_length_cap(text)

    check_rate_limit("build")

    stress_provider = stress_mod.get_provider(cfg.stress.provider)
    tts_provider = tts_mod.get_provider(cfg.tts.provider)

    log.info(
        "build.start",
        script=str(script_path),
        chars=len(text),
        stress=stress_provider.name,
        tts=tts_provider.name,
        voice=effective_voice,
    )

    annotated = stress_provider.annotate(text)
    chunks = chunk_text(annotated, tts_provider.max_chunk_chars())
    log.info("build.chunked", n_chunks=len(chunks))

    audio_format = _mime_to_format(tts_provider.output_mime())
    segments: list[AudioSegment] = []
    for i, chunk in enumerate(chunks, start=1):
        log.info("build.synthesize", chunk=f"{i}/{len(chunks)}", chars=len(chunk))
        audio_bytes = tts_provider.synthesize(chunk, effective_voice, effective_speed)
        segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format=audio_format)
        segments.append(segment)

    if not segments:
        raise RuntimeError("No audio produced (empty script?)")

    combined = segments[0]
    for segment in segments[1:]:
        combined += segment

    if out_path is None:
        audio_dir = PROJECT_ROOT / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        out_path = audio_dir / (script_path.stem + "." + cfg.tts.output_format)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    combined.export(out_path, format=cfg.tts.output_format)
    log.info("build.done", out=str(out_path), duration_ms=len(combined))
    return out_path


def _mime_to_format(mime: str) -> str:
    mapping = {
        "audio/ogg": "ogg",
        "audio/mpeg": "mp3",
        "audio/wav": "wav",
    }
    return mapping.get(mime, "ogg")


def main() -> int:
    configure_logging()
    parser = argparse.ArgumentParser(description="Build an audio episode from a script file.")
    parser.add_argument("script", type=Path, help="Path to .txt script with optional + stress marks")
    parser.add_argument("--voice", type=str, default=None, help="Override config voice")
    parser.add_argument("--speed", type=float, default=None, help="Override config speed")
    parser.add_argument("--out", type=Path, default=None, help="Override output path")
    args = parser.parse_args()

    if not args.script.exists():
        print(f"Script not found: {args.script}", file=sys.stderr)
        return 1

    out = build(args.script, out_path=args.out, voice=args.voice, speed=args.speed)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
