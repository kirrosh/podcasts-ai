"""SaluteSpeech (Sber) TTS provider — REST synthesis with SSML.

Converts Yandex-style `+vowel` stress marks into Sber-style `vowel'` apostrophe
markup, wraps text in <speak>...</speak>, and streams OGG Opus back. Access
tokens are cached in-process (TTL ≈ 30 min).

Auth setup:
1. Register at https://developers.sber.ru, create a SaluteSpeech personal
   cabinet.
2. Hit "Get key" — Sber issues a ready base64 `Authorization key` of the form
   `<client_id>:<client_secret>` already encoded. Copy it verbatim.
3. Put it in `.env` as `SBER_AUTH_KEY`. Optionally set `SBER_SCOPE`
   (defaults to `SALUTE_SPEECH_PERS` for individuals).
"""

from __future__ import annotations

import logging
import re
import time
import uuid

import httpx

from podcasts.config import ensure_secret, load_secrets
from podcasts.tts._stress_utils import scrub_stray_plus

log = logging.getLogger(__name__)

_OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
_SYNTH_URL = "https://smartspeech.sber.ru/rest/v1/text:synthesize"

# voice_<sr>: Russian neural voices (HQ variants at 24 kHz).
# Nec — Natalia (female narrator), May — Marfa (female), Ost — Alexandra (female),
# Bys — Boris (male), Tur — Taras (male), Pon — Sergey (male).
_SUPPORTED_VOICES = [
    "Nec_24000", "May_24000", "Ost_24000",
    "Bys_24000", "Tur_24000", "Pon_24000",
    "Nec_8000", "May_8000", "Ost_8000",
    "Bys_8000", "Tur_8000", "Pon_8000",
]

# Yandex format: `+vowel` (before). Sber format: `vowel'` (after).
_VOWELS = "аеёиоуыэюяАЕЁИОУЫЭЮЯ"
_PLUS_BEFORE_VOWEL = re.compile(r"\+([" + _VOWELS + r"])")

# Safety: strip XML-reserved chars from the generated text before embedding in SSML.
_XML_ESCAPE = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}


class SaluteSpeechTTS:
    """Sber SaluteSpeech REST synthesizer with SSML stress marks."""

    name = "salutespeech"

    def __init__(self) -> None:
        secrets = load_secrets()
        self._auth_key = ensure_secret(secrets.sber_auth_key, "SBER_AUTH_KEY")
        self._scope = secrets.sber_scope or "SALUTE_SPEECH_PERS"
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        # Both Sber endpoints (OAuth + synthesis) use the Minstry-of-Digital-
        # Development CA chain (russiantrustedca.pem), which is not in macOS's
        # default trust store. For a local dev spike we disable TLS verification
        # on both. TODO: ship the Minstry CA bundle for production.
        self._tls_verify = False

    def synthesize(self, text: str, voice: str, speed: float = 1.0) -> bytes:
        """Synthesize one chunk, return OGG Opus bytes."""
        if voice not in _SUPPORTED_VOICES:
            log.warning("Voice %r not in known list; trying anyway", voice)

        clean = scrub_stray_plus(text)
        ssml = _to_ssml(clean, speed=speed)

        token = self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/ssml",
        }
        params = {"voice": voice, "format": "opus"}

        with httpx.Client(timeout=30.0, verify=self._tls_verify) as client:
            resp = client.post(_SYNTH_URL, params=params, headers=headers, content=ssml.encode("utf-8"))
            if resp.status_code == 401:
                # Token expired mid-flight — refresh once and retry.
                self._token = None
                token = self._get_token()
                headers["Authorization"] = f"Bearer {token}"
                resp = client.post(_SYNTH_URL, params=params, headers=headers, content=ssml.encode("utf-8"))
            resp.raise_for_status()
            return resp.content

    def supported_voices(self) -> list[str]:
        return list(_SUPPORTED_VOICES)

    def max_chunk_chars(self) -> int:
        # SaluteSpeech REST hard limit is 4000 chars per request including SSML
        # tags. Leave margin for the <speak> wrapper and apostrophes.
        return 3800

    def output_mime(self) -> str:
        return "audio/ogg"

    def _get_token(self) -> str:
        """Fetch-and-cache OAuth2 access token (TTL ≈ 30 min)."""
        now = time.time()
        if self._token and now < self._token_expires_at - 60:
            return self._token

        headers = {
            "Authorization": f"Basic {self._auth_key}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        data = {"scope": self._scope}

        with httpx.Client(timeout=15.0, verify=self._tls_verify) as client:
            resp = client.post(_OAUTH_URL, headers=headers, data=data)
            resp.raise_for_status()
            payload = resp.json()

        self._token = payload["access_token"]
        # `expires_at` is a Unix timestamp in ms
        self._token_expires_at = int(payload["expires_at"]) / 1000.0
        log.info("SaluteSpeech token refreshed (valid until %d)", int(self._token_expires_at))
        return self._token


def _to_ssml(text: str, speed: float = 1.0) -> str:
    """Convert `+vowel` marks to Sber `vowel'` and wrap in <speak>."""
    # Escape XML before inserting apostrophes (apostrophe itself is not reserved).
    for ch, esc in _XML_ESCAPE.items():
        text = text.replace(ch, esc)
    text = _PLUS_BEFORE_VOWEL.sub(r"\1'", text)
    if abs(speed - 1.0) < 1e-3:
        return f"<speak>{text}</speak>"
    # <paint> is Sber's prosody tag. speed is a multiplier (0.5..2.0 safe range).
    return f'<speak><paint speed="{speed:.2f}">{text}</paint></speak>'
