"""Structured logging setup with secret scrubbing."""

from __future__ import annotations

import logging
import re

import structlog


_SECRET_PATTERNS = [
    re.compile(r"(Api-Key\s+)([A-Za-z0-9_\-]+)"),
    re.compile(r"(Bearer\s+)([A-Za-z0-9_\-\.]+)"),
    re.compile(r"(\"?token\"?\s*[:=]\s*\"?)([A-Za-z0-9_\-\.]+)"),
]


def _scrub_secrets(_logger, _method, event_dict):
    for key, value in list(event_dict.items()):
        if not isinstance(value, str):
            continue
        for pattern in _SECRET_PATTERNS:
            value = pattern.sub(r"\1***REDACTED***", value)
        event_dict[key] = value
    return event_dict


def configure(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _scrub_secrets,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
