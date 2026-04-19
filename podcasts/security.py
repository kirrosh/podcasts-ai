"""Safety utilities: sanitization, length caps, simple rate limiting."""

from __future__ import annotations

import json
import unicodedata
from datetime import UTC, datetime, timedelta
from pathlib import Path

from podcasts.config import PROJECT_ROOT, load_config

_CONTROL_CHARS = {chr(c) for c in range(32)} - {"\n", "\t", "\r"}

_RATE_LIMIT_FILE = PROJECT_ROOT / "state" / "rate_limit.jsonl"


def sanitize_for_tts(text: str) -> str:
    """Normalize unicode and strip control chars before feeding to any TTS provider."""
    text = unicodedata.normalize("NFC", text)
    cleaned = "".join(ch for ch in text if ch not in _CONTROL_CHARS)
    # Collapse excessive whitespace
    while "   " in cleaned:
        cleaned = cleaned.replace("   ", "  ")
    return cleaned.strip()


def enforce_length_cap(text: str, max_chars: int | None = None) -> str:
    """Raise if text exceeds the configured hard cap."""
    cfg = load_config().security
    limit = max_chars if max_chars is not None else cfg.max_script_chars
    if len(text) > limit:
        raise ValueError(
            f"Script exceeds max_script_chars={limit} (got {len(text)}). "
            f"Split into multiple episodes or raise the cap in config.toml."
        )
    return text


def check_rate_limit(kind: str = "build") -> None:
    """Raise if too many actions of `kind` occurred in the last 24h."""
    cfg = load_config().security
    limit = cfg.rate_limit_per_day

    _RATE_LIMIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=24)

    entries: list[dict] = []
    if _RATE_LIMIT_FILE.exists():
        for line in _RATE_LIMIT_FILE.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                ts = datetime.fromisoformat(entry["ts"])
                if ts > cutoff and entry.get("kind") == kind:
                    entries.append(entry)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

    if len(entries) >= limit:
        raise RuntimeError(
            f"Rate limit hit: {len(entries)}/{limit} {kind!r} actions in the last 24h. "
            f"Raise security.rate_limit_per_day in config.toml if intentional."
        )

    _append_rate_entry(now, kind)


def _append_rate_entry(ts: datetime, kind: str) -> None:
    entry = {"ts": ts.isoformat(), "kind": kind}
    with _RATE_LIMIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
