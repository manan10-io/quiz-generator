"""
language_detector.py — Detects which languages/scripts are present in text
or should be hinted to the OCR engine.

Two use cases:
  1. Pre-OCR: the user can specify expected languages, or we can default
     to the configured set (English + Hindi + Gujarati).
  2. Post-OCR: detect which Unicode scripts actually appear in the
     extracted text, used by the cleaner for script-specific normalisation
     and by the parser for selecting the right answer-keyword patterns.
"""

import re
from dataclasses import dataclass


# Unicode block ranges for the scripts we support
DEVANAGARI_RANGE = (0x0900, 0x097F)   # Hindi, Marathi, Sanskrit, etc.
GUJARATI_RANGE = (0x0A80, 0x0AFF)
LATIN_RANGE = (0x0041, 0x024F)        # Basic Latin + Latin Extended

# Tesseract language codes
TESSERACT_LANG_MAP = {
    "english": "eng",
    "hindi": "hin",
    "gujarati": "guj",
}


@dataclass
class ScriptStats:
    latin_chars: int
    devanagari_chars: int
    gujarati_chars: int
    total_chars: int

    @property
    def has_hindi(self) -> bool:
        # Threshold of 3 to handle short Devanagari passages in mixed text
        return self.devanagari_chars > 3

    @property
    def has_gujarati(self) -> bool:
        return self.gujarati_chars > 3

    @property
    def has_english(self) -> bool:
        # Threshold of 3 so that short mixed-script strings like
        # "Question: भारत (India)" still correctly flag Latin script present
        return self.latin_chars > 3

    @property
    def dominant_script(self) -> str:
        counts = {
            "devanagari": self.devanagari_chars,
            "gujarati": self.gujarati_chars,
            "latin": self.latin_chars,
        }
        return max(counts, key=lambda k: counts[k]) if self.total_chars else "latin"


class LanguageDetector:
    """Detects scripts present in text and recommends Tesseract language strings."""

    def detect_scripts(self, text: str) -> ScriptStats:
        latin = devanagari = gujarati = 0

        for ch in text:
            code = ord(ch)
            if DEVANAGARI_RANGE[0] <= code <= DEVANAGARI_RANGE[1]:
                devanagari += 1
            elif GUJARATI_RANGE[0] <= code <= GUJARATI_RANGE[1]:
                gujarati += 1
            elif LATIN_RANGE[0] <= code <= LATIN_RANGE[1] and ch.isalpha():
                latin += 1

        return ScriptStats(
            latin_chars=latin,
            devanagari_chars=devanagari,
            gujarati_chars=gujarati,
            total_chars=len(text),
        )

    def recommend_tesseract_languages(
        self,
        text: str | None = None,
        user_hint: list[str] | None = None,
    ) -> list[str]:
        """
        Recommend which Tesseract language packs to use.

        If `text` is provided (e.g. from a first-pass English-only OCR run
        used purely for script detection), scripts found in it drive the
        recommendation. Otherwise falls back to `user_hint` or the default
        multi-language set.
        """
        if user_hint:
            return [TESSERACT_LANG_MAP.get(h.lower(), h) for h in user_hint]

        if text:
            stats = self.detect_scripts(text)
            langs = []
            if stats.has_english or stats.total_chars < 20:
                langs.append("eng")
            if stats.has_hindi:
                langs.append("hin")
            if stats.has_gujarati:
                langs.append("guj")
            if langs:
                return langs

        # Default: try all three (Tesseract supports multi-language OCR
        # natively via "eng+hin+guj" — slower but most robust for unknown input)
        return ["eng", "hin", "guj"]

    def tesseract_lang_string(self, languages: list[str]) -> str:
        """Joins language codes into Tesseract's '+'-separated format."""
        return "+".join(languages) if languages else "eng"


# ─── Singleton ────────────────────────────────────────────────────────────────
language_detector = LanguageDetector()
