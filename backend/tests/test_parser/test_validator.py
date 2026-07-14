"""
Tests for QuestionValidator — duplicate detection, missing option detection,
and validation error reporting.
"""
import pytest
from app.parser.validator import validator
from app.schemas.parser import ParsedQuestion


def make_question(text="Sample question?", a="A", b="B", c="C", d="D", answer="A", position=0):
    return ParsedQuestion(
        question_text=text,
        option_a=a, option_b=b, option_c=c, option_d=d,
        correct_answer=answer,
        position=position,
    )


class TestValidation:

    def test_valid_question_passes(self):
        q = make_question()
        questions, warnings, dups = validator.validate_all([q])
        assert questions[0].is_valid is True
        assert questions[0].validation_errors == []

    def test_missing_answer_flagged(self):
        q = make_question(answer=None)
        questions, warnings, dups = validator.validate_all([q])
        assert questions[0].is_valid is False
        assert "No correct answer detected" in questions[0].validation_errors

    def test_missing_options_flagged(self):
        q = make_question(c="", d="")
        questions, warnings, dups = validator.validate_all([q])
        assert questions[0].is_valid is False
        assert any("Missing option" in e for e in questions[0].validation_errors)

    def test_too_few_options_flagged(self):
        q = make_question(b="", c="", d="")
        questions, warnings, dups = validator.validate_all([q])
        assert any("Fewer than 2 options" in e for e in questions[0].validation_errors)

    def test_answer_references_missing_option(self):
        q = make_question(d="", answer="D")
        questions, warnings, dups = validator.validate_all([q])
        assert any("references a missing option" in e for e in questions[0].validation_errors)

    def test_duplicate_detection_removes_copy(self):
        q1 = make_question(text="What is the capital of France?", position=0)
        q2 = make_question(text="What is the capital of France?", position=1)
        q3 = make_question(text="What is the capital of Spain?", answer="B", position=2)

        questions, warnings, dups = validator.validate_all(
            [q1, q2, q3], remove_duplicates=True
        )
        assert len(questions) == 2
        assert dups == 1
        assert any("Duplicate removed" in w for w in warnings)

    def test_near_duplicate_detected(self):
        """Questions with minor wording differences should still be caught."""
        q1 = make_question(text="What is the capital city of France?", position=0)
        q2 = make_question(text="What is the capital city of France ?", position=1)

        questions, warnings, dups = validator.validate_all(
            [q1, q2], remove_duplicates=True
        )
        assert len(questions) == 1
        assert dups == 1

    def test_duplicates_kept_when_disabled(self):
        q1 = make_question(text="Same question?", position=0)
        q2 = make_question(text="Same question?", position=1)

        questions, warnings, dups = validator.validate_all(
            [q1, q2], remove_duplicates=False
        )
        assert len(questions) == 2
        assert dups == 0

    def test_positions_reassigned_after_dedup(self):
        q1 = make_question(text="First?", position=0)
        q2 = make_question(text="First?", position=1)  # duplicate
        q3 = make_question(text="Second?", answer="B", position=2)

        questions, _, _ = validator.validate_all([q1, q2, q3])
        positions = [q.position for q in questions]
        assert positions == [0, 1]  # re-indexed after removing the duplicate

    def test_negative_marks_invalid(self):
        q = make_question()
        q.marks = -1
        questions, warnings, dups = validator.validate_all([q])
        assert any("negative" in e.lower() for e in questions[0].validation_errors)

    def test_empty_question_text_invalid(self):
        q = make_question(text="ab")  # too short
        questions, warnings, dups = validator.validate_all([q])
        assert questions[0].is_valid is False
