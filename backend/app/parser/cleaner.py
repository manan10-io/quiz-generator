"""
cleaner.py — Pre-processing pipeline for raw MCQ text.

Handles:
- Encoding normalization (UTF-8, Windows-1252, mojibake)
- OCR artifact removal (stray characters, broken symbols)
- Whitespace normalization (tabs, multiple spaces, CRLF)
- Line continuity repair (broken lines from OCR/PDF extraction)
- Common OCR substitution errors (0→O, 1→l/I, rn→m, etc.)
- Devanagari and Gujarati script normalization
"""

import re
import unicodedata
from typing import Optional


# ─── OCR common substitution errors ─────────────────────────────────────────

# These are character-level OCR mistakes that must be fixed in context
# Only applied to Latin-script portions
OCR_CHAR_FIXES = [
    # Stray pipe / bar characters (common in scanned tables)
    (r"(?<!\|)\|(?!\|)", " "),
    # l (ell) confused with 1 (one) at start of numbered options
    (r"^l\.", "1.", re.MULTILINE),
    # rn confused with m
    (r"\brn\b", "m"),
    # Missing space after period in numbered list
    (r"(\d+)\.([A-Z])", r"\1. \2"),
    # Double-space cleanup (run last)
]

# ─── Encoding fixes ───────────────────────────────────────────────────────────

MOJIBAKE_MAP = {
    "\u00e2\u0080\u0099": "'",   # â€™ → '
    "\u00e2\u0080\u009c": '"',   # â€œ → "
    "\u00e2\u0080\u009d": '"',   # â€ → "
    "\u00e2\u0080\u0093": "–",   # â€" → –
    "\u00e2\u0080\u0094": "—",   # â€" → —
    "\u00c2\u00a0": " ",         # Â\xa0 → space (non-breaking)
    "\u00ef\u00bb\u00bf": "",    # BOM
}

# ─── Main Cleaner class ───────────────────────────────────────────────────────


class TextCleaner:
    """
    Cleans raw text before it reaches the parser.
    Returns a cleaned string and a list of applied repair notes.
    """

    def __init__(self, aggressive: bool = False):
        """
        aggressive: enable OCR character-level substitutions.
        Use only when text is known to be OCR output.
        """
        self.aggressive = aggressive
        self._repairs: list[str] = []

    def clean(self, text: str) -> tuple[str, list[str]]:
        """
        Full cleaning pipeline.
        Returns (cleaned_text, list_of_repair_notes).
        """
        self._repairs = []

        text = self._fix_encoding(text)
        text = self._normalize_unicode(text)
        text = self._normalize_line_endings(text)
        text = self._remove_bom(text)
        text = self._fix_common_ocr_artifacts(text)
        text = self._normalize_whitespace(text)
        text = self._fix_option_letters(text)
        text = self._repair_broken_question_lines(text)
        text = self._normalize_answer_keywords(text)
        text = self._remove_page_numbers(text)
        text = self._deduplicate_blank_lines(text)

        return text.strip(), self._repairs

    # ─── Step 1: Encoding ─────────────────────────────────────────────────────

    def _fix_encoding(self, text: str) -> str:
        for bad, good in MOJIBAKE_MAP.items():
            if bad in text:
                text = text.replace(bad, good)
                self._repairs.append("Fixed encoding artifacts")
        return text

    # ─── Step 2: Unicode normalization ───────────────────────────────────────

    def _normalize_unicode(self, text: str) -> str:
        # NFC normalization — composited form for Devanagari/Gujarati
        normalized = unicodedata.normalize("NFC", text)
        if normalized != text:
            self._repairs.append("Normalized Unicode (NFC)")
        return normalized

    # ─── Step 3: Line endings ─────────────────────────────────────────────────

    def _normalize_line_endings(self, text: str) -> str:
        # Windows CRLF → LF, old Mac CR → LF
        return text.replace("\r\n", "\n").replace("\r", "\n")

    # ─── Step 4: BOM removal ─────────────────────────────────────────────────

    def _remove_bom(self, text: str) -> str:
        if text.startswith("\ufeff"):
            self._repairs.append("Removed BOM")
            return text[1:]
        return text

    # ─── Step 5: OCR artifacts ───────────────────────────────────────────────

    def _fix_common_ocr_artifacts(self, text: str) -> str:
        original = text

        # Remove form-feed characters
        text = text.replace("\x0c", "\n")

        # Replace fancy quotes with straight quotes
        text = re.sub(r"[''‚]", "'", text)
        text = re.sub(r'[""„]', '"', text)

        # Replace en/em dash with hyphen where used as separator
        text = re.sub(r"\s[–—]\s", " - ", text)

        # Remove zero-width characters
        text = re.sub(r"[\u200b\u200c\u200d\ufeff\u00ad]", "", text)

        # Remove soft hyphens (­)
        text = re.sub(r"\u00ad", "", text)

        # Remove control characters except newline/tab
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

        if self.aggressive:
            # Fix 0→O confusion in answer letters: "Answer: 0" → "Answer: O"
            text = re.sub(
                r"(Answer|Ans|Correct)[:\s]+0\b",
                lambda m: m.group(0).replace("0", "O"),
                text,
                flags=re.IGNORECASE,
            )

        if text != original:
            self._repairs.append("Removed OCR artifacts")
        return text

    # ─── Step 6: Whitespace ──────────────────────────────────────────────────

    def _normalize_whitespace(self, text: str) -> str:
        # Tabs → spaces
        text = text.replace("\t", "    ")
        # Multiple spaces within a line → single space
        lines = text.split("\n")
        cleaned = []
        for line in lines:
            # Collapse multiple spaces but preserve leading indentation context
            cleaned.append(re.sub(r" {2,}", " ", line).rstrip())
        return "\n".join(cleaned)

    # ─── Step 7: Fix option letter patterns ──────────────────────────────────

    def _fix_option_letters(self, text: str) -> str:
        """
        Normalise common OCR option-letter corruptions:
        - '(a)' → '(A)'
        - 'a.' at line start → 'A.'
        - 'a)' at line start → 'A)'
        """
        # Lowercase option letters at line start → uppercase
        text = re.sub(
            r"^([a-e])([\.\)])",
            lambda m: m.group(1).upper() + m.group(2),
            text,
            flags=re.MULTILINE,
        )
        # Lowercase in parentheses at line start: (a) → (A)
        text = re.sub(
            r"^\(([a-e])\)",
            lambda m: f"({m.group(1).upper()})",
            text,
            flags=re.MULTILINE,
        )
        return text

    # ─── Step 8: Repair broken question lines ────────────────────────────────

    def _repair_broken_question_lines(self, text: str) -> str:
        """
        PDF extractors and OCR often break a single logical line into multiple
        short lines. Detect and re-join them.

        Heuristic: if a line does NOT start with a known pattern (question
        number, option letter, answer keyword) AND the previous line does not
        end with punctuation, treat them as a continuation.
        """
        OPTION_START = re.compile(
            r"^(\d+[\.\)]|[A-Ea-e][\.\)]|\([A-Ea-e]\)|Q\d+[\.\)]|"
            r"Option\s+[A-D]|ans(wer)?[:\s]|correct[:\s]|"
            r"Topic|Subject|Chapter|Section|Marks?[:=]|Points?[:=]|"
            r"Difficulty|Level[:=]|Explanation|Rationale|Solution|Reason|Note|Exp[:.])",
            re.IGNORECASE,
        )
        SENTENCE_END = re.compile(r"[.?!:।]\s*$")

        lines = text.split("\n")
        result: list[str] = []
        i = 0
        repaired = 0

        while i < len(lines):
            line = lines[i]

            # If next line exists and current line seems incomplete
            if (
                i + 1 < len(lines)
                and line.strip()
                and not SENTENCE_END.search(line)
                and not OPTION_START.match(lines[i + 1].strip())
                and lines[i + 1].strip()
                and len(line.strip()) < 80  # short line suggests break
                and not OPTION_START.match(line.strip())
            ):
                # Merge current line with next
                result.append(line.rstrip() + " " + lines[i + 1].strip())
                i += 2
                repaired += 1
            else:
                result.append(line)
                i += 1

        if repaired:
            self._repairs.append(f"Repaired {repaired} broken line(s)")

        return "\n".join(result)

    # ─── Step 9: Normalize answer keywords ───────────────────────────────────

    def _normalize_answer_keywords(self, text: str) -> str:
        """
        Standardise the many ways answer lines appear so the answer detector
        has a consistent surface to work with.
        """
        # Gujarati / Hindi transliteration → English
        # NOTE: order matters — longest/most-specific patterns first, and the
        # short "ans" pattern uses \b word boundaries so it never matches
        # inside the word "Answer" itself (which would otherwise corrupt
        # "Answer: B" into "Answer: wer: B").
        replacements = [
            # Gujarati
            (r"(?i)ઉત્તર\s*[:：]?\s*", "Answer: "),
            (r"(?i)સાચો\s*જવાબ\s*[:：]?\s*", "Answer: "),
            # Hindi
            (r"(?i)उत्तर\s*[:：]?\s*", "Answer: "),
            (r"(?i)सही\s*उत्तर\s*[:：]?\s*", "Answer: "),
            # Most specific English variants first
            (r"(?i)correct\s+answer\s*[=:]\s*", "Answer: "),
            (r"(?i)correct\s+option\s*[=:]\s*", "Answer: "),
            (r"(?i)right\s+answer\s*[=:]\s*", "Answer: "),
            (r"(?i)answer\s+is\s*[=:]?\s*", "Answer: "),
            (r"(?i)\bkey\s*[=:]\s*", "Answer: "),
            # Short "ans" token — \b prevents matching inside "Answer"
            (r"(?i)\bans\b\s*[:\.]?\s*", "Answer: "),
        ]

        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text)

        return text

    # ─── Step 10: Remove page numbers ────────────────────────────────────────

    def _remove_page_numbers(self, text: str) -> str:
        """Remove lines that contain only a page number."""
        lines = text.split("\n")
        cleaned = [
            line
            for line in lines
            if not re.match(r"^\s*-?\s*\d+\s*-?\s*$", line)
            and not re.match(r"^\s*Page\s+\d+\s*(of\s+\d+)?\s*$", line, re.IGNORECASE)
        ]
        if len(cleaned) < len(lines):
            self._repairs.append(f"Removed {len(lines) - len(cleaned)} page number line(s)")
        return "\n".join(cleaned)

    # ─── Step 11: Blank lines ─────────────────────────────────────────────────

    def _deduplicate_blank_lines(self, text: str) -> str:
        """Collapse 3+ consecutive blank lines to 2."""
        return re.sub(r"\n{3,}", "\n\n", text)


# ─── Convenience function ─────────────────────────────────────────────────────

def clean_text(text: str, aggressive: bool = False) -> tuple[str, list[str]]:
    """Clean raw text and return (cleaned, repairs)."""
    return TextCleaner(aggressive=aggressive).clean(text)
