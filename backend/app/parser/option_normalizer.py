"""
option_normalizer.py — Extracts and normalizes MCQ options from a text block.

Converts all option styles into a standard dict: {"A": text, "B": text, ...}

Supported styles:
  A. text       A) text       (A) text      [A] text
  A: text       Option A text Option A: text
  1. text       1) text       (1) text      (numeric → A/B/C/D)
  a. text       a) text       (a) text      (lowercase → uppercase)
"""

import re
from typing import Optional


NUMERIC_TO_LETTER = {"1": "A", "2": "B", "3": "C", "4": "D", "5": "E"}

# All option prefix patterns in priority order
_OPTION_REGEXES: list[tuple[str, re.Pattern]] = [
    # (A) or [A]
    ("paren",    re.compile(r"^\s*[\(\[]\s*([A-Ea-e1-5])\s*[\)\]]\s*[.:]?\s*(.+)", re.DOTALL)),
    # A. or A) or A: with text on same line — whitespace after the marker is
    # optional to tolerate OCR output like "A.Au" (missing space)
    ("dot",      re.compile(r"^\s*([A-Ea-e])\s*[\.\):]\s*(.+)", re.DOTALL)),
    # Option A or Option A: or Option A.
    ("opt_word", re.compile(r"^\s*Option\s+([A-Ea-e1-5])\s*[.:\s]\s*(.+)", re.IGNORECASE | re.DOTALL)),
    # 1. or 1) — numeric
    ("num",      re.compile(r"^\s*([1-5])\s*[\.\)]\s*(.+)", re.DOTALL)),
    # 1: — numeric colon
    ("num_col",  re.compile(r"^\s*([1-5])\s*:\s*(.+)", re.DOTALL)),
]


class OptionNormalizer:
    """
    Parses option lines from a question block and returns a dict
    mapping A/B/C/D/E → option text.
    Also returns the lines that were NOT recognized as options.
    """

    def extract(
        self,
        lines: list[str],
    ) -> tuple[dict[str, str], list[str]]:
        """
        Returns (options_dict, remaining_lines).
        options_dict maps "A" → text, etc.
        remaining_lines are non-option lines (question, answer, blank).
        """
        options: dict[str, str] = {}
        remaining: list[str] = []
        current_letter: Optional[str] = None
        current_text: list[str] = []

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                if current_letter:
                    current_text.append("")
                continue

            matched = False
            for _, pattern in _OPTION_REGEXES:
                m = pattern.match(line)
                if m:
                    # Save previous option
                    if current_letter:
                        options[current_letter] = " ".join(
                            t for t in current_text if t
                        ).strip()

                    raw_letter = m.group(1).upper()
                    current_letter = NUMERIC_TO_LETTER.get(raw_letter, raw_letter)
                    current_text = [m.group(2).strip()]
                    matched = True
                    break

            if not matched:
                if current_letter:
                    # Continuation of current option text
                    current_text.append(line)
                else:
                    remaining.append(raw_line)

        # Save last option
        if current_letter:
            options[current_letter] = " ".join(t for t in current_text if t).strip()

        return options, remaining

    def normalise_option_text(self, text: str) -> str:
        """Strip trailing/leading artifacts from option text."""
        # Remove trailing period (common in MCQ printing)
        text = text.rstrip(".")
        # Collapse internal whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()


# Singleton
option_normalizer = OptionNormalizer()
