"""
Tests for all 7 MCQ formats described in the product specification.
Each test verifies the parser correctly extracts question text, all four
options, and the correct answer letter.
"""
import pytest
from app.parser.text_parser import text_parser
from app.schemas.parser import ParseOptions


class TestNumberedDotFormat:
    """Format: '1. Question' / 'A. Option' / 'Answer: B'"""

    def test_basic_extraction(self, default_options):
        text = """
1. What is AI?
A. Apple
B. Artificial Intelligence
C. Animal Intelligence
D. Automatic Input
Answer : B
"""
        result = text_parser.parse(text, default_options, "test")
        assert result.total_found == 1

        q = result.questions[0]
        assert q.question_text == "What is AI?"
        assert q.option_a == "Apple"
        assert q.option_b == "Artificial Intelligence"
        assert q.option_c == "Animal Intelligence"
        assert q.option_d == "Automatic Input"
        assert q.correct_answer == "B"
        assert q.is_valid is True

    def test_multiple_questions(self, default_options):
        text = """
1. What is 2+2?
A. 3
B. 4
C. 5
D. 6
Answer: B

2. What is the capital of France?
A. London
B. Berlin
C. Paris
D. Madrid
Answer: C
"""
        result = text_parser.parse(text, default_options, "test")
        assert result.total_found == 2
        assert result.questions[0].correct_answer == "B"
        assert result.questions[1].correct_answer == "C"


class TestParenQuestionFormat:
    """Format: 'Q1)' / '(A)' options / 'Ans:B'"""

    def test_basic_extraction(self, default_options):
        text = """
Q1) What is the capital of India?
(A) Mumbai
(B) Delhi
(C) Kolkata
(D) Chennai
Ans:B
"""
        result = text_parser.parse(text, default_options, "test")
        assert result.total_found == 1

        q = result.questions[0]
        assert "capital of India" in q.question_text
        assert q.option_b == "Delhi"
        assert q.correct_answer == "B"


class TestEqualsAnswerFormat:
    """Format: 'A) text' options / 'Correct Answer=C'"""

    def test_basic_extraction(self, default_options):
        text = """
What is the boiling point of water at sea level?
A) 90 degrees Celsius
B) 100 degrees Celsius
C) 110 degrees Celsius
D) 120 degrees Celsius
Correct Answer=B
"""
        result = text_parser.parse(text, default_options, "test")
        assert result.total_found == 1
        assert result.questions[0].correct_answer == "B"
        assert result.questions[0].option_b == "100 degrees Celsius"


class TestNumericOptionsFormat:
    """Format: numeric options '1) 2) 3) 4)' / 'Answer : 2'"""

    def test_numeric_to_letter_mapping(self, default_options):
        text = """
Which of these is a prime number?
1) 4
2) 7
3) 9
4) 10
Answer : 2
"""
        result = text_parser.parse(text, default_options, "test")
        assert result.total_found == 1

        q = result.questions[0]
        # Numeric option 2 should map to letter B
        assert q.option_a == "4"
        assert q.option_b == "7"
        assert q.correct_answer == "B"


class TestOptionWordFormat:
    """Format: 'Option A text' / 'Correct Option: B'"""

    def test_basic_extraction(self, default_options):
        text = """
Who wrote the Indian Constitution?
Option A Mahatma Gandhi
Option B B.R. Ambedkar
Option C Jawaharlal Nehru
Option D Sardar Patel
Correct Option : B
"""
        result = text_parser.parse(text, default_options, "test")
        assert result.total_found == 1
        assert result.questions[0].option_b == "B.R. Ambedkar"
        assert result.questions[0].correct_answer == "B"


class TestMixedLanguageFormat:
    """Hindi and Gujarati MCQ text with localized answer keywords."""

    def test_hindi_question(self, default_options):
        text = """
1. भारत की राजधानी क्या है?
A. मुंबई
B. दिल्ली
C. कोलकाता
D. चेन्नई
उत्तर: B
"""
        result = text_parser.parse(text, default_options, "test")
        assert result.total_found == 1
        assert result.questions[0].correct_answer == "B"

    def test_gujarati_question(self, default_options):
        text = """
1. ભારતની રાજધાની શું છે?
A. મુંબઈ
B. દિલ્હી
C. કોલકાતા
D. ચેન્નઈ
ઉત્તર: B
"""
        result = text_parser.parse(text, default_options, "test")
        assert result.total_found == 1
        assert result.questions[0].correct_answer == "B"


class TestOCRBrokenFormat:
    """OCR-extracted text with missing spaces and extra whitespace."""

    def test_missing_space_after_option_marker(self, default_options):
        text = """
1. What is the chemical symbol for Gold?
A.Au
B. Ag
C. Fe
D. Pb
Answer:A
"""
        result = text_parser.parse(text, default_options, "test")
        assert result.total_found == 1
        q = result.questions[0]
        assert q.option_a == "Au"
        assert q.correct_answer == "A"
        assert q.is_valid is True

    def test_extra_spaces_in_question(self, default_options):
        text = """
2.   What   is  the    chemical  symbol  for  Gold?
A. Au
B. Ag
C. Fe
D. Pb
Answer: A
"""
        result = text_parser.parse(text, default_options, "test")
        assert result.total_found == 1
        # Extra internal whitespace should be collapsed
        assert "  " not in result.questions[0].question_text
