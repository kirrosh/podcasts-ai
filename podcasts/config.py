"""Configuration loading from config.toml + .env."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TTSConfig(BaseModel):
    provider: str = "yandex"
    voice: str = "marina"
    speed: float = 1.0
    output_format: Literal["mp3", "ogg"] = "mp3"
    # F5-TTS provider: paths relative to project root (ignored by other providers).
    f5_reference_audio: str = "scripts/f5_ref/reference.wav"
    f5_reference_text: str = "scripts/f5_ref/reference.txt"


class STTConfig(BaseModel):
    provider: str = "yandex"
    model: str = "general"


class StressConfig(BaseModel):
    provider: str = "ruaccent"
    ruaccent_model: str = "turbo"


class StyleConfig(BaseModel):
    default: str = "documentary"


class PodcastConfig(BaseModel):
    chars_per_minute: int = 900
    default_minutes: int = 12


class SecurityConfig(BaseModel):
    rate_limit_per_day: int = 15
    max_script_chars: int = 50000


class VaultConfig(BaseModel):
    path: str = "vault"


class AppConfig(BaseModel):
    tts: TTSConfig = Field(default_factory=TTSConfig)
    stt: STTConfig = Field(default_factory=STTConfig)
    stress: StressConfig = Field(default_factory=StressConfig)
    style: StyleConfig = Field(default_factory=StyleConfig)
    podcast: PodcastConfig = Field(default_factory=PodcastConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    vault: VaultConfig = Field(default_factory=VaultConfig)

    @property
    def vault_path(self) -> Path:
        p = Path(self.vault.path)
        return p if p.is_absolute() else PROJECT_ROOT / p


class Secrets(BaseSettings):
    """Env-only secrets. Never commit to repo."""

    yc_api_key: str = ""
    yc_folder_id: str = ""
    telegram_bot_token: str = ""
    # SaluteSpeech (Sber) TTS: base64 Authorization key from ЛК + scope.
    sber_auth_key: str = ""
    sber_scope: str = "SALUTE_SPEECH_PERS"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def load_config(config_path: Path | None = None) -> AppConfig:
    """Read config.toml and build typed AppConfig."""
    path = config_path or PROJECT_ROOT / "config.toml"
    if not path.exists():
        return AppConfig()
    with path.open("rb") as f:
        data = tomllib.load(f)
    return AppConfig(**data)


def load_secrets() -> Secrets:
    """Load secrets from .env + environment variables."""
    return Secrets()


def ensure_secret(value: str, name: str) -> str:
    """Raise with a clear message if a required secret is missing."""
    if not value:
        raise RuntimeError(
            f"Required secret {name!r} is empty. Set it in .env "
            f"(see .env.example) or via environment variable."
        )
    return value
