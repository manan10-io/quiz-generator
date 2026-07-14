"""
validator.py — Post-parse validation for parsed questions.

Checks each ParsedQuestion for:
  - Missing question text
  - Fewer than 2 options
  - Missing options B, C, D (if A exists)
  - Empty option text
  - Missing correct answer
  - Duplicate options within a question
  - Duplicate questions across the set
  - Marks validity

Sets is_valid = False and populates validation_errors list for each issue.
Returns a list of global warnings (duplicates, etc.).
"""

import re
from typing import Optional
from difflib import SequenceMatcher

from app.schemas.parser import ParsedQuestion


def _similarity(a: str, b: str) -> float:
    """Normalized similarity ratio between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


class QuestionValidator:

    # Threshold above which two questions are considered duplicates
    DUPLICATE_THRESHOLD = 0.92

    def validate_all(
        self,
        questions: list[ParsedQuestion],
        remove_duplicates: bool = True,
    ) -> tuple[list[ParsedQuestion], list[str], int]:
        """
        Validate all questions.
        Returns (validated_questions, global_warnings, duplicates_removed_count).
        """
        global_warnings: list[str] = []
        duplicates_removed = 0

        # 1. Validate each question individually
        for q in questions:
            self._validate_single(q)

        # 2. Detect and optionally remove duplicates
        seen_texts: list[str] = []
        unique_questions: list[ParsedQuestion] = []

        for q in questions:
            q_text = q.question_text.lower().strip()
            is_dup = False

            for seen in seen_texts:
                if _similarity(q_text, seen) >= self.DUPLICATE_THRESHOLD:
                    is_dup = True
                    duplicates_removed += 1
                    preview = q.question_text[:60]
                    global_warnings.append(
                        f"Duplicate removed: \"{preview}…\""
                    )
                    break

            if not is_dup:
                seen_texts.append(q_text)
                unique_questions.append(q)

        if not remove_duplicates:
            unique_questions = questions
            duplicates_removed = 0

        # 3. Re-assign positions after duplicate removal
        for idx, q in enumerate(unique_questions):
            q.position = idx

        # 4. Global warnings
        no_answer_count = sum(1 for q in unique_questions if not q.correct_answer)
        if no_answer_count > 0:
            global_warnings.append(
                f"{no_answer_count} question(s) have no detected answer"
            )

        invalid_count = sum(1 for q in unique_questions if not q.is_valid)
        if invalid_count > 0:
            global_warnings.append(
                f"{invalid_count} question(s) have validation errors"
            )

        return unique_questions, global_warnings, duplicates_removed

    # ─── Single question validation ───────────────────────────────────────────

    def _validate_single(self, q: ParsedQuestion) -> None:
        errors: list[str] = []

        # Question text
        if not q.question_text or len(q.question_text.strip()) < 3:
            errors.append("Question text is missing or too short")

        # Minimum options
        options = {
            "A": q.option_a, "B": q.option_b,
            "C": q.option_c, "D": q.option_d,
        }
        non_empty = {k: v for k, v in options.items() if v and v.strip()}

        if len(non_empty) < 2:
            errors.append("Fewer than 2 options found")
        elif len(non_empty) < 4:
            missing = [k for k in "ABCD" if k not in non_empty]
            errors.append(f"Missing option(s): {', '.join(missing)}")

        # Empty option text
        for letter, text in non_empty.items():
            if not text.strip():
                errors.append(f"Option {letter} is empty")

        # Duplicate options
        texts = [v.strip().lower() for v in non_empty.values() if v.strip()]
        if len(texts) != len(set(texts)):
            errors.append("Duplicate option text detected")

        # Missing answer
        if not q.correct_answer:
            errors.append("No correct answer detected")

        # Answer references missing option
        if q.correct_answer and q.correct_answer not in non_empty:
            errors.append(
                f"Correct answer '{q.correct_answer}' references a missing option"
            )

        # Marks validity
        if q.marks < 0:
            errors.append("Marks cannot be negative")

        q.validation_errors = errors
        q.is_valid = len(errors) == 0


# Singleton
validator = QuestionValidator()
