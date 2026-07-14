"""
answer_detector.py — Extracts correct answers from MCQ text blocks.

Handles all common answer formats:
  - "Answer: B"         - "Ans:B"          - "Correct Answer=C"
  - "Answer : (B)"      - "Key: 2"          - "Correct Option: D"
  - Numeric → letter    - Inline bold       - End-of-block pattern
"""

import re
from typing import Optional

from app.parser.pattern_matcher import ANSWER_PATTERNS


# Numeric option index → answer letter
NUMERIC_TO_LETTER = {"1": "A", "2": "B", "3": "C", "4": "D", "5": "E"}

# Letter normalisation (handles lowercase + variant chars)
LETTER_NORMALISE = {
    "a": "A", "b": "B", "c": "C", "d": "D", "e": "E",
    "A": "A", "B": "B", "C": "C", "D": "D", "E": "E",
}


class AnswerDetector:
    """
    Tries multiple strategies to extract the correct-answer letter
    from a question block. Returns None if no answer is found.
    """

    def detect(
        self,
        block: str,
        has_numeric_options: bool = False,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Returns (answer_letter, answer_line_text).
        answer_letter is one of A/B/C/D/E or None.
        answer_line_text is the raw matched line (for removal from block).
        """
        # Strategy 1: named answer keywords
        result = self._detect_named(block)
        if result[0]:
            return result

        # Strategy 2: trailing parenthetical — "(B)" alone on last line
        result = self._detect_trailing_paren(block)
        if result[0]:
            return result

        # Strategy 3: inline bold or bracket in last line
        result = self._detect_inline_marker(block)
        if result[0]:
            return result

        return None, None

    # ─── Strategy 1: Named keyword ────────────────────────────────────────────

    def _detect_named(self, block: str) -> tuple[Optional[str], Optional[str]]:
        for pattern in ANSWER_PATTERNS:
            match = pattern.regex.search(block)
            if match:
                raw = match.group(1).strip()
                letter = self._normalise(raw)
                if letter:
                    return letter, match.group(0).strip()
        return None, None

    # ─── Strategy 2: Trailing paren e.g. "(B)" on its own line ───────────────

    def _detect_trailing_paren(self, block: str) -> tuple[Optional[str], Optional[str]]:
        lines = [l.strip() for l in block.strip().split("\n") if l.strip()]
        if not lines:
            return None, None

        # Check last 3 lines for a lone letter in parens
        for line in reversed(lines[-3:]):
            m = re.fullmatch(r"\(?([A-Ea-e1-4])\)?", line)
            if m:
                letter = self._normalise(m.group(1))
                if letter:
                    return letter, line
        return None, None

    # ─── Strategy 3: Inline bold / bracket markers ────────────────────────────

    def _detect_inline_marker(self, block: str) -> tuple[Optional[str], Optional[str]]:
        # **B** or [B] or *B*
        m = re.search(r"[\*\[]+([A-Ea-e])[\*\]]+", block)
        if m:
            letter = self._normalise(m.group(1))
            if letter:
                return letter, m.group(0)
        return None, None

    # ─── Normalisation helper ─────────────────────────────────────────────────

    def _normalise(self, raw: str) -> Optional[str]:
        raw = raw.strip().upper()
        if raw in ("A", "B", "C", "D", "E"):
            return raw
        if raw in NUMERIC_TO_LETTER:
            return NUMERIC_TO_LETTER[raw]
        return None

    # ─── Remove answer line from block text ──────────────────────────────────

    def strip_answer_line(self, block: str, answer_line: Optional[str]) -> str:
        """Remove the matched answer line from the block."""
        if not answer_line:
            return block
        # Remove the full line that contains the answer marker
        lines = block.split("\n")
        cleaned = [
            line for line in lines
            if answer_line.strip() not in line
        ]
        return "\n".join(cleaned)


# ─── Convenience singleton ────────────────────────────────────────────────────
answer_detector = AnswerDetector()
