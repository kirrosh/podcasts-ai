"""No-op stress annotator — pass text through unchanged. Useful for debugging."""

from __future__ import annotations


class NoopStress:
    name = "noop"

    def annotate(self, text: str) -> str:
        return text
