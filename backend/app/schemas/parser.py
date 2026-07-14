from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


# ─── Parse options ────────────────────────────────────────────────────────────

class ParseOptions(BaseModel):
    ai_cleanup: bool = True
    remove_duplicates: bool = True
    auto_number: bool = False
    detect_topics: bool = True
    default_marks: float = Field(default=1.0, ge=0, le=100)
    default_difficulty: Optional[Literal["easy", "medium", "hard"]] = None

    @field_validator("default_difficulty", mode="before")
    @classmethod
    def empty_default_difficulty_is_none(cls, value):
        return None if value == "" else value


# ─── Parsed question (intermediate) ──────────────────────────────────────────

class ParsedQuestion(BaseModel):
    question_number: Optional[int] = None
    question_text: str
    option_a: str = ""
    option_b: str = ""
    option_c: str = ""
    option_d: str = ""
    option_e: str = ""
    correct_answer: Optional[Literal["A", "B", "C", "D", "E"]] = None
    marks: float = 1.0
    negative_marks: float = 0.0
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    topic: Optional[str] = None
    explanation: Optional[str] = None
    position: int = 0
    is_valid: bool = True
    validation_errors: list[str] = Field(default_factory=list)

    @field_validator("question_text", "option_a", "option_b", "option_c", "option_d")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip() if v else v

    @property
    def has_all_options(self) -> bool:
        return all([self.option_a, self.option_b, self.option_c, self.option_d])

    @property
    def option_count(self) -> int:
        return sum(
            1 for opt in [self.option_a, self.option_b, self.option_c, self.option_d, self.option_e]
            if opt
        )


# ─── Parse request / response ─────────────────────────────────────────────────

class ParseTextRequest(BaseModel):
    text: str = Field(..., min_length=5, description="Raw MCQ text to parse")
    project_id: Optional[str] = None
    options: ParseOptions = Field(default_factory=ParseOptions)


class ParseResult(BaseModel):
    job_id: str
    questions: list[ParsedQuestion]
    warnings: list[str]
    duplicates_removed: int
    parse_duration_ms: int
    format_detected: Optional[str] = None
    total_found: int


# ─── Parse job status ─────────────────────────────────────────────────────────

class ParseJobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "ocr", "parsing", "ai_clean", "done", "failed"]
    progress: int = 0
    message: str = ""
    questions_found: int = 0
    warnings: list[str] = Field(default_factory=list)
    error_message: Optional[str] = None
