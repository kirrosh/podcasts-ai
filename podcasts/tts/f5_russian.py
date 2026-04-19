"""F5-TTS Russian provider — local neural synthesis via Misha24-10/F5-TTS_RUSSIAN.

Zero-shot voice cloning from a reference WAV + its transcript. Reads `+vowel`
stress marks identically to Yandex — no conversion required. Runs on Apple
Silicon via PyTorch MPS.

First call downloads ~1.8 GB (checkpoint + vocab + Vocos vocoder) into the HF
cache; subsequent calls are offline.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

from podcasts.config import PROJECT_ROOT, load_config
from podcasts.tts._stress_utils import scrub_stray_plus

log = logging.getLogger(__name__)

_HF_REPO = "Misha24-10/F5-TTS_RUSSIAN"
_CKPT_FILE = "F5TTS_v1_Base_v2/model_last_inference.safetensors"
# vocab.txt is shared across v1 checkpoints and lives only in F5TTS_v1_Base.
_VOCAB_FILE = "F5TTS_v1_Base/vocab.txt"


class F5RussianTTS:
    """F5-TTS for Russian with voice cloning from a reference clip."""

    name = "f5_russian"

    def __init__(self) -> None:
        # Heavy imports are deferred until the provider is actually instantiated
        # (keeps module-level import of `podcasts.tts` lightweight).
        import soundfile as sf
        from f5_tts.api import F5TTS
        from huggingface_hub import hf_hub_download

        self._sf = sf

        cfg = load_config().tts
        ref_audio_path = _resolve(cfg.f5_reference_audio)
        ref_text_path = _resolve(cfg.f5_reference_text)
        if not ref_audio_path.exists():
            raise FileNotFoundError(
                f"F5 reference audio not found: {ref_audio_path}. "
                f"Place a mono 24kHz WAV (~10s) there or override tts.f5_reference_audio."
            )
        if not ref_text_path.exists():
            raise FileNotFoundError(
                f"F5 reference transcript not found: {ref_text_path}. "
                f"Create it with the exact text of the reference audio, `+ударения` allowed."
            )
        self._ref_audio = str(ref_audio_path)
        self._ref_text = ref_text_path.read_text(encoding="utf-8").strip()

        log.info("Downloading F5-TTS_RUSSIAN weights if needed (first call may take a while)")
        ckpt_path = hf_hub_download(repo_id=_HF_REPO, filename=_CKPT_FILE)
        vocab_path = hf_hub_download(repo_id=_HF_REPO, filename=_VOCAB_FILE)

        self._tts = F5TTS(
            model="F5TTS_v1_Base",
            ckpt_file=ckpt_path,
            vocab_file=vocab_path,
            device="mps",
        )
        log.info("F5-TTS_RUSSIAN loaded (Misha24-10/v2, device=mps)")

    def synthesize(self, text: str, voice: str, speed: float = 1.0) -> bytes:
        """Generate a single chunk. `voice` is ignored — timbre comes from ref_audio."""
        clean = scrub_stray_plus(text)
        wav, sr, _ = self._tts.infer(
            ref_file=self._ref_audio,
            ref_text=self._ref_text,
            gen_text=clean,
            speed=speed,
            show_info=lambda *_a, **_k: None,
        )
        buf = io.BytesIO()
        self._sf.write(buf, wav, sr, format="WAV", subtype="PCM_16")
        return buf.getvalue()

    def supported_voices(self) -> list[str]:
        return ["default"]

    def max_chunk_chars(self) -> int:
        return 500

    def output_mime(self) -> str:
        return "audio/wav"


def _resolve(p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else PROJECT_ROOT / path
