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
        #
        # Occurrences are position-indexed so homographs with different stress in
        # the same document (e.g. `Д+ухи прошлого` and later `дух+и французской`)
        # each restore to their own original form.
        existing = self._capture_existing_ordered(text)
        stripped = text.replace("+", "")
        accented = self._safe_process(stripped)
        yandex_format = self._combining_to_plus(accented)
        return self._restore_ordered(yandex_format, existing)

    def _safe_process(self, text: str) -> str:
        """Run RUAccent; if the bundled ONNX model blows up on an OOV word, fall
        back to per-paragraph then per-word, leaving offenders unaccented.

        Background: RUAccent 1.5.x ships an ONNX accent model whose exported
        inputs (`input_ids`, `attention_mask`) don't match what the library
        feeds it (`token_type_ids` also required). For words that land in the
        neural fallback path (rare names, hyphenated surnames, unusual
        prefixes) the whole `process_all` call raises and the pipeline dies.
        """
        try:
            return self._accent.process_all(text)
        except Exception as exc:  # noqa: BLE001 — upstream raises bare ValueError
            log.warning("RUAccent full-text failed (%s); falling back per paragraph", exc)

        out: list[str] = []
        for para in text.split("\n"):
            if not para.strip():
                out.append(para)
                continue
            try:
                out.append(self._accent.process_all(para))
            except Exception:
                out.append(self._safe_per_word(para))
        return "\n".join(out)

    def _safe_per_word(self, text: str) -> str:
        def repl(match: re.Match[str]) -> str:
            token = match.group(0)
            try:
                return self._accent.process_all(token)
            except Exception:
                return token

        return re.sub(r"\w+", repl, text, flags=re.UNICODE)

    @staticmethod
    def _capture_existing_ordered(text: str) -> dict[str, list[str]]:
        """Return {stripped_lower: [original1, original2, ...]} preserving order."""
        result: dict[str, list[str]] = {}
        for match in re.finditer(r"\w+\+\w*", text, flags=re.UNICODE):
            original = match.group(0)
            stripped = original.replace("+", "").lower()
            result.setdefault(stripped, []).append(original)
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
    def _restore_ordered(text: str, existing: dict[str, list[str]]) -> str:
        """Replace each word occurrence with its user-provided original, in order."""
        if not existing:
            return text
        cursors: dict[str, int] = {k: 0 for k in existing}

        def repl(match: re.Match[str]) -> str:
            word = match.group(0)
            bare = word.replace("+", "").lower()
            variants = existing.get(bare)
            if not variants:
                return word
            idx = cursors[bare]
            if idx >= len(variants):
                # More occurrences than user marked — leave RUAccent's version alone.
                return word
            cursors[bare] = idx + 1
            return variants[idx]

        return re.sub(r"\w+\+?\w*", repl, text, flags=re.UNICODE)
