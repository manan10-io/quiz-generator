"""
Tests for the AnswerDetector — covers every answer-line style the spec
requires the parser to tolerate.
"""
import pytest
from app.parser.answer_detector import answer_detector


class TestAnswerDetection:

    @pytest.mark.parametrize(
        "answer_line,expected",
        [
            ("Answer: B", "B"),
            ("Answer : B", "B"),
            ("Answer:B", "B"),
            ("Ans: B", "B"),
            ("Ans:B", "B"),
            ("Ans.B", "B"),
            ("Correct Answer: C", "C"),
            ("Correct Answer=C", "C"),
            ("Correct Option: D", "D"),
            ("Correct Option=D", "D"),
            ("Key: A", "A"),
            ("Answer: 2", "B"),   # numeric → letter
            ("Ans: 4", "D"),
            ("Answer: a", "A"),   # lowercase normalised
        ],
    )
    def test_named_answer_formats(self, answer_line, expected):
        block = f"Question text\nA. opt1\nB. opt2\nC. opt3\nD. opt4\n{answer_line}"
        letter, _ = answer_detector.detect(block)
        assert letter == expected

    def test_no_answer_returns_none(self):
        block = "Question text\nA. opt1\nB. opt2\nC. opt3\nD. opt4"
        letter, line = answer_detector.detect(block)
        assert letter is None
        assert line is None

    def test_trailing_paren_fallback(self):
        block = "Question text\nA. opt1\nB. opt2\nC. opt3\nD. opt4\n(C)"
        letter, _ = answer_detector.detect(block)
        assert letter == "C"

    def test_strip_answer_line_removes_correct_line(self):
        block = "Question\nA. x\nB. y\nAnswer: B\nTopic: Math"
        _, answer_line = answer_detector.detect(block)
        stripped = answer_detector.strip_answer_line(block, answer_line)
        assert "Answer" not in stripped
        assert "Topic: Math" in stripped
