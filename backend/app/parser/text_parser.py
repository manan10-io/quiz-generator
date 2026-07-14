"""
text_parser.py — Main MCQ parsing engine.

Pipeline:
  1. Clean raw text (cleaner.py)
  2. Detect format (pattern_matcher.py)
  3. Split into question blocks
  4. For each block:
      a. Extract question number
      b. Extract options (option_normalizer.py)
      c. Detect answer (answer_detector.py)
      d. Extract marks, difficulty, topic, explanation
      e. Apply defaults
  5. Validate all questions (validator.py)

Supports all 7 MCQ formats and mixed-language text.
"""

import re
import time
from typing import Optional

from app.schemas.parser import ParsedQuestion, ParseOptions, ParseResult
from app.parser.cleaner import clean_text
from app.parser.pattern_matcher import (
    FormatDetector, MCQFormat,
    QUESTION_NUMBER_PATTERNS, OPTION_PATTERNS,
    MARKS_PATTERNS, DIFFICULTY_PATTERNS, DIFFICULTY_MAP,
    TOPIC_PATTERNS, EXPLANATION_PATTERNS,
)
from app.parser.answer_detector import answer_detector
from app.parser.option_normalizer import option_normalizer
from app.parser.validator import validator


class TextParser:
    """
    Parses raw MCQ text into structured ParsedQuestion objects.
    """

    def parse(
        self,
        raw_text: str,
        options: ParseOptions,
        job_id: str = "sync",
    ) -> ParseResult:
        start_ms = int(time.time() * 1000)
        all_warnings: list[str] = []

        # ── Step 1: Clean ──────────────────────────────────────────────────
        cleaned, repair_notes = clean_text(raw_text, aggressive=True)
        if repair_notes:
            all_warnings.extend(repair_notes)

        # ── Step 2: Detect format ─────────────────────────────────────────
        detected_format, _scores = FormatDetector.detect(cleaned)

        # ── Step 3: Split into question blocks ────────────────────────────
        blocks = self._split_into_blocks(cleaned, detected_format)

        if not blocks:
            all_warnings.append("No question blocks detected in the input text")
            return ParseResult(
                job_id=job_id,
                questions=[],
                warnings=all_warnings,
                duplicates_removed=0,
                parse_duration_ms=int(time.time() * 1000) - start_ms,
                format_detected=detected_format.value,
                total_found=0,
            )

        # ── Step 4: Parse each block ──────────────────────────────────────
        questions: list[ParsedQuestion] = []
        for idx, block in enumerate(blocks):
            q = self._parse_block(block, idx, options, detected_format)
            if q:
                questions.append(q)

        if not questions:
            all_warnings.append("Blocks were found but no questions could be extracted")

        # ── Step 5: Validate ──────────────────────────────────────────────
        questions, validation_warnings, duplicates_removed = validator.validate_all(
            questions, remove_duplicates=options.remove_duplicates
        )
        all_warnings.extend(validation_warnings)

        elapsed = int(time.time() * 1000) - start_ms

        return ParseResult(
            job_id=job_id,
            questions=questions,
            warnings=all_warnings,
            duplicates_removed=duplicates_removed,
            parse_duration_ms=elapsed,
            format_detected=detected_format.value,
            total_found=len(questions),
        )

    # ─── Block splitting ──────────────────────────────────────────────────────

    def _split_into_blocks(self, text: str, fmt: MCQFormat) -> list[str]:
        """
        Split cleaned text into individual question blocks using a line-by-line
        state machine. This is robust to blank lines between options (a common
        pasting artifact) and correctly disambiguates numeric option markers
        ("1) 2) 3) 4)") from question numbering ("1. Question text").

        Algorithm:
          - Blank lines are skipped entirely (never treated as boundaries).
          - A line matching an option pattern (A./A)/(A)/Option A/numeric 1-4
            in sequence) is appended to the current block as an option.
          - A line matching an answer pattern is appended as the answer.
          - Any other line is question text — UNLESS the current block has
            already collected options or an answer, in which case it signals
            the start of a NEW question block.
          - Numeric option lines (1/2/3/4) are only accepted as options when
            they continue a valid increasing sequence starting at 1; this
            prevents a genuine "2. Next question" from being swallowed as
            option "2" of the previous question.
        """
        lines = [l for l in text.split("\n") if l.strip()]
        if not lines:
            return []

        blocks: list[str] = []
        current: list[str] = []
        in_options = False
        got_answer = False
        next_expected_numeric = 1
        numeric_sequence_active = False

        def flush():
            nonlocal current, in_options, got_answer, next_expected_numeric, numeric_sequence_active
            if current:
                blocks.append("\n".join(current))
            current = []
            in_options = False
            got_answer = False
            next_expected_numeric = 1
            numeric_sequence_active = False

        for line in lines:
            stripped = line.strip()

            letter_opt = self._match_letter_option(stripped)
            numeric_opt = self._match_numeric_option(stripped)
            is_answer = self._match_answer_line(stripped)
            is_metadata = self._match_metadata_line(stripped)

            # Numeric option lines are only valid as options once the block
            # already has question text AND the sequence is consistent
            # (must start at 1, then increase by 1 each time).
            is_valid_numeric_opt = False
            if numeric_opt is not None and current:
                if not numeric_sequence_active and numeric_opt == 1:
                    is_valid_numeric_opt = True
                elif numeric_sequence_active and numeric_opt == next_expected_numeric:
                    is_valid_numeric_opt = True

            if letter_opt is not None and current:
                current.append(line)
                in_options = True
                continue

            if is_valid_numeric_opt:
                current.append(line)
                in_options = True
                numeric_sequence_active = True
                next_expected_numeric = numeric_opt + 1
                continue

            if is_answer and current:
                current.append(line)
                got_answer = True
                continue

            # Metadata lines (Topic:, Difficulty:, Marks:, Explanation:, etc.)
            # belong to the current question regardless of where they appear
            # (often after the answer) — never treat them as a new question.
            if is_metadata and current:
                current.append(line)
                continue

            # ── This line is plain text (question text or a new question) ──
            if in_options or got_answer:
                # We were collecting options/answer for a previous question —
                # this fresh text line starts a NEW question block.
                flush()
                current = [line]
            else:
                # Still accumulating question text (e.g. multi-line question)
                current.append(line)

        flush()

        # Filter out any degenerate blocks that are too short to be real
        return [b for b in blocks if len(b.strip()) > 8]

    # ─── Line classifiers used by the block-splitting state machine ──────────

    def _match_letter_option(self, line: str) -> Optional[str]:
        """Returns the letter (A-E) if line starts with a letter-option marker."""
        for pattern in OPTION_PATTERNS:
            m = pattern.regex.match(line)
            if m:
                letter = m.group(1).upper()
                if letter in ("A", "B", "C", "D", "E"):
                    return letter
        return None

    def _match_numeric_option(self, line: str) -> Optional[int]:
        """Returns the digit (1-5) if line starts with a numeric-option marker."""
        m = re.match(r"^([1-5])[\.\):]\s+\S", line)
        if m:
            return int(m.group(1))
        return None

    def _match_answer_line(self, line: str) -> bool:
        """True if line matches any known answer-keyword pattern."""
        from app.parser.pattern_matcher import ANSWER_PATTERNS
        return any(p.regex.match(line) for p in ANSWER_PATTERNS)

    def _match_metadata_line(self, line: str) -> bool:
        """
        True if line is a labelled metadata line (Topic:, Difficulty:, Marks:,
        Explanation:, etc.) that should attach to the current question rather
        than start a new one. These commonly appear AFTER the answer line.
        """
        return bool(re.match(
            r"^(Topic|Subject|Chapter|Section|Marks?|Points?|"
            r"Difficulty|Level|Explanation|Rationale|Solution|Reason|Note|Exp)"
            r"\s*[:=]",
            line,
            re.IGNORECASE,
        ))

    # ─── Single block parser ──────────────────────────────────────────────────

    def _parse_block(
        self,
        block: str,
        position: int,
        options: ParseOptions,
        fmt: MCQFormat,
    ) -> Optional[ParsedQuestion]:
        if not block.strip():
            return None

        lines = block.split("\n")

        # 1. Extract question number + strip it from first line
        question_number, first_line_stripped = self._extract_question_number(lines[0])

        # 2. Detect answer first (so we can strip the answer line)
        answer_letter, answer_line = answer_detector.detect(block)
        block_no_answer = answer_detector.strip_answer_line(block, answer_line)
        lines_no_answer = block_no_answer.split("\n")

        # 3. Extract options from the BODY only (excludes the headline at
        #    index 0, which we already captured above as first_line_stripped).
        #    Without this exclusion the headline gets duplicated into both
        #    first_line_stripped and question_parts below.
        body_lines = lines_no_answer[1:]
        opts, remaining_lines = option_normalizer.extract(body_lines)

        # 4. Remaining lines form the question text
        # The first remaining line(s) after stripping the question number.
        # Metadata lines (Topic:, Difficulty:, Marks:, Explanation:, etc.) and
        # any stray answer-keyword lines are excluded — they're extracted
        # separately in step 5 and must not leak into the question text.
        question_parts: list[str] = []
        for line in remaining_lines:
            stripped = line.strip()
            if not stripped:
                continue
            # Skip if this looks like the question number header
            if question_number and re.match(r"^Q?\.?\s*\d+[\.\)]\s*", stripped, re.IGNORECASE):
                continue
            if self._match_metadata_line(stripped):
                continue
            if self._match_answer_line(stripped):
                continue
            question_parts.append(stripped)

        # Reconstruct question text
        # The very first line (stripped of question number) is usually the Q
        if question_parts:
            question_text = self._build_question_text(
                first_line_stripped, question_parts, opts
            )
        else:
            question_text = first_line_stripped

        if not question_text or len(question_text) < 3:
            return None

        # 5. Extract marks, difficulty, topic, explanation from block
        marks = self._extract_marks(block) or options.default_marks
        difficulty = self._extract_difficulty(block) or options.default_difficulty
        topic = self._extract_topic(block) if options.detect_topics else None
        explanation = self._extract_explanation(block_no_answer)

        # 6. Normalise option texts
        for letter in list(opts.keys()):
            opts[letter] = option_normalizer.normalise_option_text(opts[letter])

        q = ParsedQuestion(
            question_number=question_number,
            question_text=question_text,
            option_a=opts.get("A", ""),
            option_b=opts.get("B", ""),
            option_c=opts.get("C", ""),
            option_d=opts.get("D", ""),
            option_e=opts.get("E", ""),
            correct_answer=answer_letter,
            marks=marks,
            negative_marks=0.0,
            difficulty=difficulty,
            topic=topic,
            explanation=explanation,
            position=position,
        )
        return q

    # ─── Question text extraction ─────────────────────────────────────────────

    def _build_question_text(
        self,
        first_line: str,
        remaining: list[str],
        opts: dict[str, str],
    ) -> str:
        """
        Combine first_line and any remaining lines that are NOT options.
        """
        opt_values = set(v.lower().strip() for v in opts.values() if v)

        parts = [first_line] if first_line.strip() else []
        for line in remaining:
            # Don't add lines that match option text
            if line.strip().lower() in opt_values:
                continue
            # Don't add lines that look like answer markers
            if re.match(r"^Answer\s*[:=]", line.strip(), re.IGNORECASE):
                continue
            parts.append(line.strip())

        text = " ".join(p for p in parts if p)
        # Collapse internal whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    # ─── Sub-extractors ───────────────────────────────────────────────────────

    def _extract_question_number(self, first_line: str) -> tuple[Optional[int], str]:
        """
        Returns (question_number_or_None, line_with_number_removed).
        """
        for pattern in QUESTION_NUMBER_PATTERNS:
            m = pattern.regex.match(first_line)
            if m:
                try:
                    num = int(m.group(1))
                    stripped = first_line[m.end():].strip()
                    return num, stripped
                except (ValueError, IndexError):
                    stripped = first_line[m.end():].strip()
                    return None, stripped
        return None, first_line.strip()

    def _extract_marks(self, block: str) -> Optional[float]:
        for pattern in MARKS_PATTERNS:
            m = pattern.search(block)
            if m:
                try:
                    return float(m.group(1))
                except ValueError:
                    pass
        return None

    def _extract_difficulty(self, block: str) -> Optional[str]:
        for i, pattern in enumerate(DIFFICULTY_PATTERNS):
            m = pattern.search(block)
            if m:
                key = m.group(1).lower()
                return DIFFICULTY_MAP.get(key)
        return None

    def _extract_topic(self, block: str) -> Optional[str]:
        for pattern in TOPIC_PATTERNS:
            m = pattern.search(block)
            if m:
                topic = m.group(1).strip()
                if topic and len(topic) < 100:
                    return topic
        return None

    def _extract_explanation(self, block: str) -> Optional[str]:
        for pattern in EXPLANATION_PATTERNS:
            m = pattern.search(block)
            if m:
                exp = m.group(1).strip()
                if exp:
                    return exp
        return None


# ─── Singleton ────────────────────────────────────────────────────────────────
text_parser = TextParser()
