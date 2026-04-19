"""RUAccent-based Russian stress annotator (ACL 2025, 0.96 acc on homographs)."""

from __future__ import annotations

import logging
import re

from podcasts.config import load_config

log = logging.getLogger(__name__)

# RUAccent emits stress as U+0301 (combining acute) after the stressed vowel.
# We convert to Yandex-style `+гласная` for pipeline consistency.
_COMBINING_ACUTE = "\u0301"


class RuAccentStress:
    name = "ruaccent"

    def __init__(self) -> None:
        from ruaccent import RUAccent

        cfg = load_config().stress
        self._accent = RUAccent()
        # omograph_model_size: "turbo" (fast, ~300MB) | "big_poetry" (accurate, ~1GB)
        self._accent.load(
            omograph_model_size=cfg.ruaccent_model,
            use_dictionary=True,
            tiny_mode=False,
        )
        log.info("RUAccent loaded (model=%s)", cfg.ruaccent_model)

    def annotate(self, text: str) -> str:
        """Preserve existing `+` marks; annotate the rest via RUAccent."""
        # RUAccent works on text without pre-existing marks, so we temporarily strip
        # our `+` markers, run RUAccent, then restore ours on top (our marks win).
        existing = self._capture_existing(text)
        stripped = text.replace("+", "")
        accented = self._accent.process_all(stripped)
        yandex_format = self._combining_to_plus(accented)
        # Re-apply user-provided marks: split on whitespace, for each word that had
        # an explicit `+` in the original, restore that version.
        return self._restore_explicit(yandex_format, existing)

    @staticmethod
    def _capture_existing(text: str) -> dict[str, str]:
        """Return {stripped_word_lower: original_word_with_plus}."""
        result: dict[str, str] = {}
        for match in re.finditer(r"\w+\+\w*", text, flags=re.UNICODE):
            original = match.group(0)
            stripped = original.replace("+", "").lower()
            result[stripped] = original
        return result

    @staticmethod
    def _combining_to_plus(text: str) -> str:
        """Convert 'а́' (vowel + U+0301) to '+а'."""
        out: list[str] = []
        i = 0
        while i < len(text):
            ch = text[i]
            # If next char is combining acute, move '+' before the current vowel
            if i + 1 < len(text) and text[i + 1] == _COMBINING_ACUTE:
                out.append("+")
                out.append(ch)
                i += 2
            else:
                out.append(ch)
                i += 1
        return "".join(out)

    @staticmethod
    def _restore_explicit(text: str, existing: dict[str, str]) -> str:
        """Where the user explicitly placed `+`, use their version."""
        if not existing:
            return text

        def repl(match: re.Match[str]) -> str:
            word = match.group(0)
            bare = word.replace("+", "").lower()
            return existing.get(bare, word)

        return re.sub(r"\w+\+?\w*", repl, text, flags=re.UNICODE)
