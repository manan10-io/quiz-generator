"""
pattern_matcher.py — Regex patterns for all supported MCQ input formats.

Format catalogue:
  1. NUMBERED_DOT    — "1. Question\nA. Opt\nAnswer: B"
  2. NUMBERED_PAREN  — "1) Question\nA) Opt\nAns:B"
  3. Q_NUMBERED      — "Q1. / Q1) Question"
  4. PARENTHETICAL   — "(A) / [A] options"
  5. OPTION_WORD     — "Option A / Option B"
  6. NUMERIC_OPTS    — "1) 2) 3) 4) numeric options"
  7. PLAIN           — Unlabelled block, best-effort split
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MCQFormat(str, Enum):
    NUMBERED_DOT   = "numbered_dot"    # 1. Q  /  A. opt
    NUMBERED_PAREN = "numbered_paren"  # 1) Q  /  A) opt
    Q_NUMBERED     = "q_numbered"      # Q1. / Q1)
    PARENTHETICAL  = "parenthetical"   # (A) [A]
    OPTION_WORD    = "option_word"     # "Option A"
    NUMERIC_OPTS   = "numeric_opts"    # 1) 2) 3) 4) as options
    PLAIN          = "plain"           # best-effort


@dataclass
class Pattern:
    """Compiled regex pattern with metadata."""
    name: str
    regex: re.Pattern
    priority: int = 0  # higher → tried first


# ─── Question-number patterns ─────────────────────────────────────────────────

QUESTION_NUMBER_PATTERNS: list[Pattern] = [
    Pattern("q_paren",     re.compile(r"^Q\.?\s*(\d+)\s*[\.\)]\s*", re.MULTILINE | re.IGNORECASE), 10),
    Pattern("num_dot",     re.compile(r"^(\d{1,3})\.\s+", re.MULTILINE), 9),
    Pattern("num_paren",   re.compile(r"^(\d{1,3})\)\s+", re.MULTILINE), 8),
    Pattern("num_bracket", re.compile(r"^\[(\d{1,3})\]\s+", re.MULTILINE), 7),
    Pattern("num_colon",   re.compile(r"^(\d{1,3})\s*:\s+", re.MULTILINE), 6),
]

# ─── Option-letter patterns ───────────────────────────────────────────────────

OPTION_PATTERNS: list[Pattern] = [
    # (A) style
    Pattern("paren_upper",  re.compile(r"^\(([A-Ea-e])\)\s*(.+)", re.MULTILINE), 10),
    # [A] style
    Pattern("bracket_upper",re.compile(r"^\[([A-Ea-e])\]\s*(.+)", re.MULTILINE), 9),
    # A. style — whitespace after the dot is optional to tolerate OCR output
    # like "A.Au" (missing space), per spec requirement to handle this.
    Pattern("dot_upper",    re.compile(r"^([A-Ea-e])\.\s*(.+)", re.MULTILINE), 8),
    # A) style — same tolerance for missing space
    Pattern("paren_upper2", re.compile(r"^([A-Ea-e])\)\s*(.+)", re.MULTILINE), 7),
    # A: style
    Pattern("colon_upper",  re.compile(r"^([A-Ea-e]):\s*(.+)", re.MULTILINE), 6),
    # "Option A" style
    Pattern("option_word",  re.compile(r"^Option\s+([A-Ea-e])[:\s]\s*(.+)", re.MULTILINE | re.IGNORECASE), 5),
    # Numeric 1) 2) 3) 4) — options numbered
    Pattern("numeric_opt",  re.compile(r"^([1-4])\)\s*(.+)", re.MULTILINE), 4),
    Pattern("numeric_dot",  re.compile(r"^([1-4])\.\s*(.+)", re.MULTILINE), 4),
]

# ─── Answer-line patterns ─────────────────────────────────────────────────────

ANSWER_PATTERNS: list[Pattern] = [
    # "Answer: B" / "Answer : B" / "Answer=B"
    Pattern("ans_colon",  re.compile(
        r"^Answer\s*[=:\s]\s*([A-Ea-e1-4])\b",
        re.MULTILINE | re.IGNORECASE
    ), 10),
    # "Ans: B" / "Ans:B"
    Pattern("ans_short",  re.compile(
        r"^Ans\s*[\.:\s]\s*([A-Ea-e1-4])\b",
        re.MULTILINE | re.IGNORECASE
    ), 9),
    # "Correct Answer: B" / "Correct Answer=B"
    Pattern("correct_ans",re.compile(
        r"^Correct\s+(?:Answer|Option|Ans)\s*[=:\s]\s*([A-Ea-e1-4])\b",
        re.MULTILINE | re.IGNORECASE
    ), 10),
    # "(B)" alone on a line — likely the answer
    Pattern("lone_paren", re.compile(
        r"^Answer\s*:\s*\(([A-Ea-e])\)",
        re.MULTILINE | re.IGNORECASE
    ), 8),
    # Key: B
    Pattern("key_colon",  re.compile(
        r"^Key\s*[=:\s]\s*([A-Ea-e1-4])\b",
        re.MULTILINE | re.IGNORECASE
    ), 7),
    # Bold/markers: **B** or [B]
    Pattern("bold_ans",   re.compile(
        r"^Answer\s*[=:\s]\s*[\*\[]*([A-Ea-e1-4])[\*\]]*\b",
        re.MULTILINE | re.IGNORECASE
    ), 6),
]

# ─── Marks / points patterns ─────────────────────────────────────────────────

MARKS_PATTERNS: list[Pattern] = [
    re.compile(r"\[(\d+(?:\.\d+)?)\s*(?:marks?|pts?|points?)\]", re.IGNORECASE),
    re.compile(r"\((\d+(?:\.\d+)?)\s*(?:marks?|pts?|points?)\)", re.IGNORECASE),
    re.compile(r"marks?\s*[:=]\s*(\d+(?:\.\d+)?)", re.IGNORECASE),
]

# ─── Difficulty patterns ──────────────────────────────────────────────────────

DIFFICULTY_PATTERNS: list[Pattern] = [
    re.compile(r"\b(easy|simple|basic)\b", re.IGNORECASE),
    re.compile(r"\b(medium|moderate|average|normal)\b", re.IGNORECASE),
    re.compile(r"\b(hard|difficult|tough|challenging|advanced)\b", re.IGNORECASE),
]

DIFFICULTY_MAP = {
    "easy": "easy", "simple": "easy", "basic": "easy",
    "medium": "medium", "moderate": "medium", "average": "medium", "normal": "medium",
    "hard": "hard", "difficult": "hard", "tough": "hard",
    "challenging": "hard", "advanced": "hard",
}

# ─── Topic / subject patterns ─────────────────────────────────────────────────

TOPIC_PATTERNS = [
    re.compile(r"^Topic\s*[:=]\s*(.+)", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^Subject\s*[:=]\s*(.+)", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^Chapter\s*[:=]\s*(.+)", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^Section\s*[:=]\s*(.+)", re.MULTILINE | re.IGNORECASE),
]

# ─── Explanation / rationale patterns ────────────────────────────────────────

EXPLANATION_PATTERNS = [
    re.compile(r"^(?:Explanation|Rationale|Solution|Reason|Note)\s*[:]\s*(.+?)(?=\n\n|\Z)", re.MULTILINE | re.IGNORECASE | re.DOTALL),
    re.compile(r"^Exp\s*[:]\s*(.+)", re.MULTILINE | re.IGNORECASE),
]

# ─── Format detection ────────────────────────────────────────────────────────

class FormatDetector:
    """
    Analyses a cleaned text block and returns the most likely MCQFormat,
    along with confidence scores for each candidate.
    """

    @staticmethod
    def detect(text: str) -> tuple[MCQFormat, dict[MCQFormat, float]]:
        scores: dict[MCQFormat, float] = {fmt: 0.0 for fmt in MCQFormat}

        # Count occurrences of each format signal
        q_numbered      = len(re.findall(r"^Q\.?\s*\d+[\.\)]", text, re.MULTILINE | re.IGNORECASE))
        num_dot         = len(re.findall(r"^\d{1,3}\.\s+\S", text, re.MULTILINE))
        num_paren       = len(re.findall(r"^\d{1,3}\)\s+\S", text, re.MULTILINE))
        opt_paren       = len(re.findall(r"^\([A-Ea-e]\)", text, re.MULTILINE))
        opt_dot         = len(re.findall(r"^[A-Ea-e]\.\s", text, re.MULTILINE))
        opt_paren2      = len(re.findall(r"^[A-Ea-e]\)\s", text, re.MULTILINE))
        opt_word        = len(re.findall(r"^Option\s+[A-Da-d]", text, re.MULTILINE | re.IGNORECASE))
        num_opts        = len(re.findall(r"^[1-4][\.\)]\s", text, re.MULTILINE))

        # Score each format
        if q_numbered > 0:
            scores[MCQFormat.Q_NUMBERED] += q_numbered * 3

        if num_dot > 0:
            scores[MCQFormat.NUMBERED_DOT] += num_dot * 2
            if opt_dot > 0:
                scores[MCQFormat.NUMBERED_DOT] += opt_dot

        if num_paren > 0:
            scores[MCQFormat.NUMBERED_PAREN] += num_paren * 2
            if opt_paren2 > 0:
                scores[MCQFormat.NUMBERED_PAREN] += opt_paren2

        if opt_paren > 0:
            scores[MCQFormat.PARENTHETICAL] += opt_paren * 2

        if opt_word > 0:
            scores[MCQFormat.OPTION_WORD] += opt_word * 3

        if num_opts > num_dot and num_opts > 0:
            scores[MCQFormat.NUMERIC_OPTS] += num_opts * 2

        # Default fallback
        if max(scores.values()) == 0:
            scores[MCQFormat.PLAIN] = 1.0

        best = max(scores, key=lambda k: scores[k])
        return best, scores

    @staticmethod
    def detect_option_style(lines: list[str]) -> Optional[re.Pattern]:
        """
        Given a block of lines, detect which option pattern they use.
        Returns the regex that matched most, or None.
        """
        counts: dict[Pattern, int] = {p: 0 for p in OPTION_PATTERNS}
        for line in lines[:40]:  # sample first 40 lines
            for p in OPTION_PATTERNS:
                if p.regex.match(line.strip()):
                    counts[p] += 1

        if not any(counts.values()):
            return None
        best = max(counts, key=lambda k: counts[k])
        return best.regex if counts[best] > 0 else None
