"""
ai_service.py — Claude-powered cleanup for parsed questions.

Used when:
  - A question has validation errors
  - Options are missing or garbled
  - Answer is not detected
  - OCR text has serious corruption

Calls Claude Haiku (fast + cheap) with a structured prompt and parses
the JSON response back into ParsedQuestion objects.
"""

import json
import logging
from typing import Optional

import anthropic

from app.config import settings
from app.schemas.parser import ParsedQuestion

logger = logging.getLogger(__name__)

_client: Optional[anthropic.Anthropic] = None


def _is_usable_key(key: str) -> bool:
    """
    A real Anthropic key starts with 'sk-ant-'. Treat empty values and the
    scaffolding placeholder ('sk-ant-your-key-here') as "no key configured"
    so parsing silently skips AI cleanup instead of burning time on requests
    that are guaranteed to 401.
    """
    return bool(key) and key.startswith("sk-ant-") and "your-key" not in key


def _get_client() -> Optional[anthropic.Anthropic]:
    global _client
    if not _is_usable_key(settings.ANTHROPIC_API_KEY):
        return None
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


SYSTEM_PROMPT = """You are an MCQ parser assistant. You receive a raw text block from a scanned or pasted question paper and must extract one multiple-choice question from it.

Return ONLY valid JSON — no markdown, no explanation — in this exact schema:
{
  "question_text": "The full question text",
  "option_a": "Option A text",
  "option_b": "Option B text",
  "option_c": "Option C text",
  "option_d": "Option D text",
  "option_e": "",
  "correct_answer": "A" | "B" | "C" | "D" | "E" | null,
  "marks": 1.0,
  "difficulty": "easy" | "medium" | "hard" | null,
  "topic": "topic string or null",
  "explanation": "explanation or null"
}

Rules:
- correct_answer must be exactly one letter A-E, or null if not found
- option_e is empty string if there are only 4 options
- marks defaults to 1.0 if not specified
- All text fields should be clean, properly capitalised
- Remove question numbers, option letters, and answer markers from the text fields
- If the block contains multiple questions, extract ONLY the first one"""


class AICleanupService:
    """Uses Claude to repair questions that the regex parser couldn't fully extract."""

    def cleanup_question(self, raw_block: str, broken_question: ParsedQuestion) -> Optional[ParsedQuestion]:
        """
        Send a broken question's raw block to Claude for repair.
        Returns a repaired ParsedQuestion or None if AI is not available.
        """
        client = _get_client()
        if not client or not settings.AI_CLEANUP_ENABLED:
            return None

        try:
            message = client.messages.create(
                model=settings.AI_MODEL,
                max_tokens=800,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"Extract the MCQ from this block:\n\n{raw_block[:2000]}",
                    }
                ],
            )

            raw_json = message.content[0].text.strip()
            # Strip markdown fences if Claude adds them
            raw_json = raw_json.replace("```json", "").replace("```", "").strip()

            data = json.loads(raw_json)
            return self._dict_to_question(data, broken_question)

        except (anthropic.APIError, json.JSONDecodeError, KeyError) as e:
            logger.warning("AI cleanup failed for question: %s", e)
            return None

    def cleanup_batch(
        self,
        blocks_and_questions: list[tuple[str, ParsedQuestion]],
    ) -> list[ParsedQuestion]:
        """
        Attempt AI repair for a batch of invalid questions.
        Returns the list with repaired questions where possible.
        """
        results: list[ParsedQuestion] = []
        for raw_block, q in blocks_and_questions:
            if not q.is_valid:
                repaired = self.cleanup_question(raw_block, q)
                results.append(repaired if repaired else q)
            else:
                results.append(q)
        return results

    def _dict_to_question(
        self, data: dict, original: ParsedQuestion
    ) -> ParsedQuestion:
        """Map Claude's JSON response to a ParsedQuestion."""
        def safe_str(v) -> str:
            return str(v).strip() if v else ""

        def safe_answer(v) -> Optional[str]:
            if not v:
                return None
            v = str(v).upper().strip()
            return v if v in ("A", "B", "C", "D", "E") else None

        def safe_difficulty(v) -> Optional[str]:
            if not v:
                return None
            v = str(v).lower().strip()
            return v if v in ("easy", "medium", "hard") else None

        def safe_float(v, default: float = 1.0) -> float:
            try:
                return float(v)
            except (TypeError, ValueError):
                return default

        return ParsedQuestion(
            question_number=original.question_number,
            question_text=safe_str(data.get("question_text")) or original.question_text,
            option_a=safe_str(data.get("option_a")) or original.option_a,
            option_b=safe_str(data.get("option_b")) or original.option_b,
            option_c=safe_str(data.get("option_c")) or original.option_c,
            option_d=safe_str(data.get("option_d")) or original.option_d,
            option_e=safe_str(data.get("option_e", "")),
            correct_answer=safe_answer(data.get("correct_answer")) or original.correct_answer,
            marks=safe_float(data.get("marks"), default=original.marks),
            negative_marks=original.negative_marks,
            difficulty=safe_difficulty(data.get("difficulty")) or original.difficulty,
            topic=safe_str(data.get("topic")) or original.topic,
            explanation=safe_str(data.get("explanation")) or original.explanation,
            position=original.position,
        )


# ─── Singleton ────────────────────────────────────────────────────────────────
ai_service = AICleanupService()
