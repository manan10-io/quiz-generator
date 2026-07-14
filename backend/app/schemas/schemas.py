"""
schemas — All Pydantic v2 request/response models.
One file keeps imports simple; split into sub-modules only if this grows.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ─── Auth ─────────────────────────────────────────────────────────────────────

class GoogleAuthRequest(BaseModel):
    """Payload sent by Next.js frontend after Google OAuth callback."""
    google_id: str
    email: EmailStr
    name: str
    avatar_url: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[int] = None  # Unix seconds when the Google access token expires


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    user_name: str
    user_email: str
    user_avatar: Optional[str] = None


# ─── User ─────────────────────────────────────────────────────────────────────

class UserSettings(BaseModel):
    default_marks: float = Field(default=1.0, ge=0, le=100)
    shuffle_questions: bool = False
    shuffle_options: bool = False
    theme: Literal["light", "dark", "system"] = "system"
    language: str = "en"
    default_difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    autosave_interval: int = Field(default=5, ge=1, le=60)

    @field_validator("default_difficulty", mode="before")
    @classmethod
    def empty_default_difficulty_is_none(cls, value):
        return None if value == "" else value


class UserOut(BaseModel):
    id: str
    google_id: str
    email: str
    name: str
    avatar_url: Optional[str]
    settings: UserSettings
    created_at: datetime

    model_config = {"from_attributes": True}


class UserSettingsUpdate(BaseModel):
    default_marks: Optional[float] = None
    shuffle_questions: Optional[bool] = None
    shuffle_options: Optional[bool] = None
    theme: Optional[Literal["light", "dark", "system"]] = None
    language: Optional[str] = None
    default_difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    autosave_interval: Optional[int] = Field(default=None, ge=1, le=60)

    @field_validator("default_difficulty", mode="before")
    @classmethod
    def empty_default_difficulty_is_none(cls, value):
        return None if value == "" else value


# ─── Project ──────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(default=None, max_length=2000)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=500)
    description: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[Literal["draft", "ready", "archived"]] = None


class ProjectOut(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str]
    status: str
    question_count: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_project(cls, project) -> "ProjectOut":
        return cls(
            id=project.id,
            user_id=project.user_id,
            name=project.name,
            description=project.description,
            status=project.status,
            question_count=project.question_count,
            metadata=project.metadata_ or {},
            created_at=project.created_at,
            updated_at=project.updated_at,
        )


class ProjectList(BaseModel):
    items: list[ProjectOut]
    total: int


# ─── Question ─────────────────────────────────────────────────────────────────

class QuestionCreate(BaseModel):
    question_text: str = Field(..., min_length=3, max_length=2000)
    option_a: str = Field(default="", max_length=1000)
    option_b: str = Field(default="", max_length=1000)
    option_c: str = Field(default="", max_length=1000)
    option_d: str = Field(default="", max_length=1000)
    option_e: str = Field(default="", max_length=1000)
    correct_answer: Optional[Literal["A", "B", "C", "D", "E"]] = None
    marks: float = Field(default=1.0, ge=0, le=100)
    negative_marks: float = Field(default=0.0, ge=0, le=100)
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    topic: Optional[str] = Field(default=None, max_length=255)
    explanation: Optional[str] = Field(default=None, max_length=5000)
    position: int = Field(default=0, ge=0)


class QuestionUpdate(BaseModel):
    question_text: Optional[str] = Field(default=None, min_length=3, max_length=2000)
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    option_e: Optional[str] = None
    correct_answer: Optional[Literal["A", "B", "C", "D", "E"]] = None
    marks: Optional[float] = Field(default=None, ge=0, le=100)
    negative_marks: Optional[float] = Field(default=None, ge=0, le=100)
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    topic: Optional[str] = Field(default=None, max_length=255)
    explanation: Optional[str] = Field(default=None, max_length=5000)
    is_valid: Optional[bool] = None
    validation_errors: Optional[list[str]] = None


class QuestionOut(BaseModel):
    id: str
    project_id: str
    question_number: Optional[int]
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    option_e: str
    correct_answer: Optional[str]
    marks: float
    negative_marks: float
    difficulty: Optional[str]
    topic: Optional[str]
    explanation: Optional[str]
    position: int
    is_valid: bool
    validation_errors: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuestionList(BaseModel):
    items: list[QuestionOut]
    total: int
    page: int
    page_size: int
    pages: int


class ReorderRequest(BaseModel):
    ordered_ids: list[str] = Field(..., min_length=1)


# ─── Parse (persisted) ────────────────────────────────────────────────────────

class ParsePersistResult(BaseModel):
    """
    Returned by /parse/text and /parse/file after the extracted questions have
    been written to the database. Unlike the intermediate ParsedQuestion list,
    every question here is a fully-persisted row with a real id, so the frontend
    can edit/delete/reorder it immediately without a second round-trip.
    """
    job_id: str
    questions: list[QuestionOut]
    warnings: list[str] = Field(default_factory=list)
    duplicates_removed: int = 0
    parse_duration_ms: int = 0
    total_found: int = 0
    format_detected: Optional[str] = None


# ─── Google Forms ─────────────────────────────────────────────────────────────

class GenerateFormRequest(BaseModel):
    project_id: str
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=2000)
    quiz_mode: bool = True
    shuffle_questions: bool = False
    shuffle_options: bool = False
    immediate_release: bool = True
    confirmation_message: str = Field(default="Thank you for completing the quiz!", max_length=500)


class GeneratedFormOut(BaseModel):
    id: str
    project_id: str
    user_id: str
    google_form_id: str
    google_form_url: str
    google_form_edit_url: str
    title: str
    description: Optional[str]
    question_count: int
    total_marks: float
    settings: dict[str, Any]
    generated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_form(cls, form) -> "GeneratedFormOut":
        return cls(
            id=form.id,
            project_id=form.project_id,
            user_id=form.user_id,
            google_form_id=form.google_form_id,
            google_form_url=form.google_form_url,
            google_form_edit_url=form.google_form_edit_url,
            title=form.title,
            description=form.description,
            question_count=form.question_count,
            total_marks=float(form.total_marks),
            settings=form.form_settings or {},
            generated_at=form.generated_at,
        )


class GeneratedFormList(BaseModel):
    items: list[GeneratedFormOut]


# ─── Exports ──────────────────────────────────────────────────────────────────

class ExportRecordOut(BaseModel):
    id: str
    project_id: str
    user_id: str
    format: str
    file_name: str
    file_size: Optional[int]
    download_url: Optional[str]
    expires_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class ExportHistoryList(BaseModel):
    items: list[ExportRecordOut]


class DownloadUrlResponse(BaseModel):
    url: str
    file_name: str
    expires_at: Optional[datetime]


# ─── Dashboard ────────────────────────────────────────────────────────────────

class DifficultyDistribution(BaseModel):
    easy: int = 0
    medium: int = 0
    hard: int = 0


class TopicCount(BaseModel):
    topic: str
    count: int


class DashboardStats(BaseModel):
    total_questions: int
    total_projects: int
    forms_generated: int
    parse_accuracy: int  # 0-100 percentage
    questions_this_week: int
    difficulty_distribution: DifficultyDistribution
    top_topics: list[TopicCount]
