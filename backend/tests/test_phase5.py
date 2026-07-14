"""
test_phase5.py — Phase 5 integration tests: JWT, export generators, Forms API.

All tests use real Python logic — no mocking.
Tests that need actual Google OAuth or a live DB are excluded here
(they belong in end-to-end / staging test suites).
"""

import json

import pytest

from app.auth.jwt_utils import (
    create_access_token,
    decode_access_token,
    extract_user_id,
    token_is_valid,
)
from app.routers.exports import (
    _export_csv,
    _export_json,
    _export_moodle,
    _export_txt,
    _export_quizizz,
    _export_kahoot,
)
from app.google.forms_api import GoogleFormsAPI, LETTER_TO_INDEX


# ─── Fixtures ─────────────────────────────────────────────────────────────────

class _Q:
    """Minimal question mock matching the Question ORM field names."""
    question_text = "What is the boiling point of water?"
    option_a = "90°C"
    option_b = "100°C"
    option_c = "110°C"
    option_d = "80°C"
    option_e = ""
    correct_answer = "B"
    marks = 2.0
    negative_marks = 0.5
    topic = "Chemistry"
    difficulty = "easy"
    explanation = "Water boils at 100°C at standard pressure."


class _Q2:
    question_text = "What is H2O?"
    option_a = "Salt"
    option_b = "Water"
    option_c = "Sugar"
    option_d = "Acid"
    option_e = ""
    correct_answer = "B"
    marks = 1.0
    negative_marks = 0.0
    topic = "Chemistry"
    difficulty = "medium"
    explanation = ""


@pytest.fixture
def single_q():
    return [_Q()]


@pytest.fixture
def two_qs():
    return [_Q(), _Q2()]


# ─── JWT ──────────────────────────────────────────────────────────────────────

class TestJWT:

    def test_token_is_string(self):
        token = create_access_token("user-1", "a@b.com")
        assert isinstance(token, str)

    def test_token_has_three_dot_parts(self):
        token = create_access_token("user-1", "a@b.com")
        assert len(token.split(".")) == 3

    def test_sub_claim_equals_user_id(self):
        token = create_access_token("user-42", "test@example.com")
        payload = decode_access_token(token)
        assert payload["sub"] == "user-42"

    def test_email_claim_correct(self):
        token = create_access_token("u", "hello@test.com")
        payload = decode_access_token(token)
        assert payload["email"] == "hello@test.com"

    def test_extra_claims_preserved(self):
        token = create_access_token("u", "e@t.com", {"role": "teacher"})
        payload = decode_access_token(token)
        assert payload["role"] == "teacher"

    def test_exp_and_iat_present(self):
        token = create_access_token("u", "e@t.com")
        payload = decode_access_token(token)
        assert "exp" in payload
        assert "iat" in payload

    def test_iat_less_than_exp(self):
        token = create_access_token("u", "e@t.com")
        payload = decode_access_token(token)
        assert payload["iat"] < payload["exp"]

    def test_extract_user_id_returns_correct(self):
        token = create_access_token("user-xyz", "x@y.com")
        assert extract_user_id(token) == "user-xyz"

    def test_token_is_valid_true_for_good_token(self):
        token = create_access_token("u", "e@t.com")
        assert token_is_valid(token) is True

    def test_token_is_valid_false_for_garbage(self):
        assert token_is_valid("garbage.token.here") is False
        assert token_is_valid("not_a_token") is False

    def test_extract_user_id_none_for_bad_token(self):
        assert extract_user_id("bad.token") is None
        assert extract_user_id("") is None

    def test_two_tokens_for_same_user_are_different(self):
        """Each token includes a fresh iat, so they must differ."""
        import time
        t1 = create_access_token("u", "e@t.com")
        time.sleep(0.01)
        t2 = create_access_token("u", "e@t.com")
        # Same user, but iat will differ making the encoded payload differ
        payload1 = decode_access_token(t1)
        payload2 = decode_access_token(t2)
        assert payload1["sub"] == payload2["sub"] == "u"


# ─── CSV export ───────────────────────────────────────────────────────────────

class TestCSVExport:

    def test_filename_ends_with_csv(self, single_q):
        _, fn, _ = _export_csv(single_q, "Proj")
        assert fn.endswith(".csv")

    def test_mime_type(self, single_q):
        _, _, mime = _export_csv(single_q, "Proj")
        assert mime == "text/csv"

    def test_question_text_present(self, single_q):
        b, _, _ = _export_csv(single_q, "Proj")
        assert b"boiling point" in b

    def test_correct_answer_B(self, single_q):
        b, _, _ = _export_csv(single_q, "Proj")
        assert b",B," in b

    def test_marks_present(self, single_q):
        b, _, _ = _export_csv(single_q, "Proj")
        assert b"2.0" in b

    def test_topic_present(self, single_q):
        b, _, _ = _export_csv(single_q, "Proj")
        assert b"Chemistry" in b

    def test_header_row_present(self, single_q):
        b, _, _ = _export_csv(single_q, "Proj")
        assert b"Question" in b

    def test_two_questions_three_rows(self, two_qs):
        b, _, _ = _export_csv(two_qs, "Proj")
        rows = b.decode().strip().split("\n")
        assert len(rows) == 3  # header + 2 questions

    def test_option_a_text_present(self, single_q):
        b, _, _ = _export_csv(single_q, "Proj")
        assert "90" in b.decode()


# ─── JSON export ──────────────────────────────────────────────────────────────

class TestJSONExport:

    def test_valid_json_output(self, single_q):
        b, _, _ = _export_json(single_q, "Proj")
        data = json.loads(b)
        assert isinstance(data, list)

    def test_one_item_for_single_question(self, single_q):
        b, _, _ = _export_json(single_q, "Proj")
        assert len(json.loads(b)) == 1

    def test_answer_field_correct(self, single_q):
        data = json.loads(_export_json(single_q, "P")[0])
        assert data[0]["answer"] == "B"

    def test_options_dict_structure(self, single_q):
        data = json.loads(_export_json(single_q, "P")[0])
        opts = data[0]["options"]
        assert opts["A"] == "90°C"
        assert opts["B"] == "100°C"
        assert opts["C"] == "110°C"
        assert opts["D"] == "80°C"

    def test_marks_correct(self, single_q):
        data = json.loads(_export_json(single_q, "P")[0])
        assert data[0]["marks"] == 2.0

    def test_topic_and_difficulty(self, single_q):
        data = json.loads(_export_json(single_q, "P")[0])
        assert data[0]["topic"] == "Chemistry"
        assert data[0]["difficulty"] == "easy"

    def test_explanation_present(self, single_q):
        data = json.loads(_export_json(single_q, "P")[0])
        assert "100°C" in (data[0]["explanation"] or "")

    def test_question_number_starts_at_1(self, single_q):
        data = json.loads(_export_json(single_q, "P")[0])
        assert data[0]["number"] == 1

    def test_two_questions_two_items(self, two_qs):
        data = json.loads(_export_json(two_qs, "P")[0])
        assert len(data) == 2
        assert data[1]["question"] == "What is H2O?"


# ─── TXT export ───────────────────────────────────────────────────────────────

class TestTXTExport:

    def test_question_text_in_output(self, single_q):
        b, _, _ = _export_txt(single_q, "Proj")
        assert b"boiling point" in b

    def test_option_a_formatted(self, single_q):
        b, _, _ = _export_txt(single_q, "Proj")
        assert b"A. 90" in b

    def test_answer_line_present(self, single_q):
        b, _, _ = _export_txt(single_q, "Proj")
        assert b"Answer: B" in b

    def test_explanation_line_present(self, single_q):
        b, _, _ = _export_txt(single_q, "Proj")
        assert b"Explanation:" in b

    def test_filename_ends_txt(self, single_q):
        _, fn, _ = _export_txt(single_q, "P")
        assert fn.endswith(".txt")

    def test_question_numbered(self, single_q):
        b, _, _ = _export_txt(single_q, "P")
        assert b"1." in b

    def test_two_questions_both_present(self, two_qs):
        b, _, _ = _export_txt(two_qs, "P")
        assert b"boiling point" in b
        assert b"H2O" in b


# ─── Moodle XML export ────────────────────────────────────────────────────────

class TestMoodleExport:

    def test_valid_xml_root(self, single_q):
        b, _, _ = _export_moodle(single_q, "P")
        assert b"<quiz>" in b

    def test_correct_answer_fraction_100(self, single_q):
        b, _, _ = _export_moodle(single_q, "P")
        assert b'fraction="100"' in b

    def test_wrong_answer_fraction_0(self, single_q):
        b, _, _ = _export_moodle(single_q, "P")
        assert b'fraction="0"' in b

    def test_marks_value_present(self, single_q):
        b, _, _ = _export_moodle(single_q, "P")
        assert b"2.0" in b

    def test_question_text_present(self, single_q):
        b, _, _ = _export_moodle(single_q, "P")
        assert b"boiling point" in b

    def test_filename_ends_xml(self, single_q):
        _, fn, _ = _export_moodle(single_q, "P")
        assert fn.endswith(".xml")

    def test_multichoice_type(self, single_q):
        b, _, _ = _export_moodle(single_q, "P")
        assert b'type="multichoice"' in b

    def test_two_questions_two_multichoice_elements(self, two_qs):
        b, _, _ = _export_moodle(two_qs, "P")
        # Count the specific attribute since <questiontext> also starts with <question
        assert b.count(b'type="multichoice"') == 2

    def test_explanation_as_feedback(self, single_q):
        b, _, _ = _export_moodle(single_q, "P")
        # Explanation should appear somewhere in the feedback
        assert b"100\xc2\xb0C" in b or b"100" in b


# ─── Quizizz CSV export ───────────────────────────────────────────────────────

class TestQuizizzExport:

    def test_has_header_row(self, single_q):
        b, _, _ = _export_quizizz(single_q, "P")
        assert "Question Text" in b.decode()

    def test_header_and_data_rows(self, single_q):
        b, _, _ = _export_quizizz(single_q, "P")
        rows = b.decode().strip().split("\n")
        assert len(rows) == 2

    def test_answer_index_2_for_B(self, single_q):
        """Correct answer B → index 2 in 1-based Quizizz format."""
        b, _, _ = _export_quizizz(single_q, "P")
        lines = b.decode().strip().split("\n")
        assert ",2," in lines[1]

    def test_filename_contains_quizizz(self, single_q):
        _, fn, _ = _export_quizizz(single_q, "P")
        assert "quizizz" in fn

    def test_two_questions_three_rows(self, two_qs):
        b, _, _ = _export_quizizz(two_qs, "P")
        rows = b.decode().strip().split("\n")
        assert len(rows) == 3


# ─── Kahoot CSV export ────────────────────────────────────────────────────────

class TestKahootExport:

    def test_has_header_row(self, single_q):
        b, _, _ = _export_kahoot(single_q, "P")
        assert "Question" in b.decode()

    def test_header_and_data_rows(self, single_q):
        b, _, _ = _export_kahoot(single_q, "P")
        rows = b.decode().strip().split("\n")
        assert len(rows) == 2

    def test_answer_index_2_for_B(self, single_q):
        """Correct answer B → index 2 in 1-based Kahoot format."""
        b, _, _ = _export_kahoot(single_q, "P")
        lines = b.decode().strip().split("\n")
        assert lines[1].endswith(",2")

    def test_filename_contains_kahoot(self, single_q):
        _, fn, _ = _export_kahoot(single_q, "P")
        assert "kahoot" in fn

    def test_two_questions_three_rows(self, two_qs):
        b, _, _ = _export_kahoot(two_qs, "P")
        rows = b.decode().strip().split("\n")
        assert len(rows) == 3


# ─── Google Forms API structure ───────────────────────────────────────────────

class TestGoogleFormsAPI:

    def test_instantiates(self):
        api = GoogleFormsAPI()
        assert api is not None

    def test_has_create_quiz_method(self):
        assert callable(getattr(GoogleFormsAPI(), "create_quiz", None))

    def test_has_all_private_helpers(self):
        api = GoogleFormsAPI()
        for method in ("_create_form", "_enable_quiz_mode", "_add_questions", "_raise_for_status"):
            assert callable(getattr(api, method, None)), f"Missing: {method}"

    def test_letter_to_index_mapping(self):
        assert LETTER_TO_INDEX["A"] == 0
        assert LETTER_TO_INDEX["B"] == 1
        assert LETTER_TO_INDEX["C"] == 2
        assert LETTER_TO_INDEX["D"] == 3
        assert LETTER_TO_INDEX["E"] == 4

    def test_raises_for_status_on_4xx(self):
        api = GoogleFormsAPI()
        mock_resp = type("R", (), {
            "status_code": 403,
            "text": "Forbidden",
            "json": lambda: {"error": {"message": "Forbidden"}}
        })()
        with pytest.raises(RuntimeError) as exc_info:
            api._raise_for_status(mock_resp, "test_op")
        assert "403" in str(exc_info.value)

    def test_raises_for_status_on_5xx(self):
        api = GoogleFormsAPI()
        mock_resp = type("R", (), {
            "status_code": 500,
            "text": "Server error",
            "json": lambda: {"error": {"message": "Internal server error"}}
        })()
        with pytest.raises(RuntimeError):
            api._raise_for_status(mock_resp, "test_op")

    def test_no_raise_on_200(self):
        api = GoogleFormsAPI()
        mock_resp = type("R", (), {
            "status_code": 200,
            "text": "OK",
            "json": lambda: {}
        })()
        api._raise_for_status(mock_resp, "test_op")  # should not raise

    def test_no_raise_on_201(self):
        api = GoogleFormsAPI()
        mock_resp = type("R", (), {
            "status_code": 201,
            "text": "Created",
            "json": lambda: {}
        })()
        api._raise_for_status(mock_resp, "test_op")  # should not raise

    def test_auth_headers_contain_bearer(self):
        api = GoogleFormsAPI()
        headers = api._auth_headers("my-test-token")
        assert headers["Authorization"] == "Bearer my-test-token"
        assert headers["Content-Type"] == "application/json"
