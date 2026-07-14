"""
models — SQLAlchemy ORM definitions matching the Phase 1 database schema exactly.
All timestamps are timezone-aware UTC. JSON columns use JSONB on PostgreSQL and
JSON on SQLite (SQLAlchemy handles this transparently via the JSON type).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer,
    Numeric, String, Text, UniqueConstraint, Index, event,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ─── User ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    google_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=lambda: {
        "default_marks": 1,
        "shuffle_questions": False,
        "shuffle_options": False,
        "theme": "system",
        "language": "en",
        "default_difficulty": None,
        "autosave_interval": 5,
    })
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    # Relationships
    projects: Mapped[list[Project]] = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    generated_forms: Mapped[list[GeneratedForm]] = relationship("GeneratedForm", back_populates="user", cascade="all, delete-orphan")
    export_records: Mapped[list[ExportRecord]] = relationship("ExportRecord", back_populates="user", cascade="all, delete-orphan")
    parse_jobs: Mapped[list[ParseJob]] = relationship("ParseJob", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id!r} email={self.email!r}>"


# ─── Project ──────────────────────────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_user_updated", "user_id", "updated_at"),
        Index("ix_projects_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | ready | archived
    question_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="projects")
    questions: Mapped[list[Question]] = relationship("Question", back_populates="project", cascade="all, delete-orphan", order_by="Question.position")
    generated_forms: Mapped[list[GeneratedForm]] = relationship("GeneratedForm", back_populates="project", cascade="all, delete-orphan")
    export_records: Mapped[list[ExportRecord]] = relationship("ExportRecord", back_populates="project", cascade="all, delete-orphan")
    parse_jobs: Mapped[list[ParseJob]] = relationship("ParseJob", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Project id={self.id!r} name={self.name!r}>"


# ─── Question ─────────────────────────────────────────────────────────────────

class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        Index("ix_questions_project_position", "project_id", "position"),
        Index("ix_questions_topic", "topic"),
        Index("ix_questions_difficulty", "difficulty"),
        Index("ix_questions_valid", "is_valid"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    question_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    option_a: Mapped[str] = mapped_column(Text, default="")
    option_b: Mapped[str] = mapped_column(Text, default="")
    option_c: Mapped[str] = mapped_column(Text, default="")
    option_d: Mapped[str] = mapped_column(Text, default="")
    option_e: Mapped[str] = mapped_column(Text, default="")
    correct_answer: Mapped[str | None] = mapped_column(String(5), nullable=True)  # A|B|C|D|E
    marks: Mapped[float] = mapped_column(Numeric(5, 2), default=1.0)
    negative_marks: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    difficulty: Mapped[str | None] = mapped_column(String(10), nullable=True)  # easy|medium|hard
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    validation_errors: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="questions")

    def __repr__(self) -> str:
        return f"<Question id={self.id!r} pos={self.position}>"


# ─── Parse Job ────────────────────────────────────────────────────────────────

class ParseJob(Base):
    __tablename__ = "parse_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|ocr|parsing|ai_clean|done|failed
    input_type: Mapped[str] = mapped_column(String(20), nullable=False, default="text")  # text|pdf|docx|image|txt
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cleaned_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    questions_found: Mapped[int] = mapped_column(Integer, default=0)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="parse_jobs")
    user: Mapped[User] = relationship("User", back_populates="parse_jobs")


# ─── Generated Form ───────────────────────────────────────────────────────────

class GeneratedForm(Base):
    __tablename__ = "generated_forms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    google_form_id: Mapped[str] = mapped_column(String(255), nullable=False)
    google_form_url: Mapped[str] = mapped_column(Text, nullable=False)
    google_form_edit_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_marks: Mapped[float] = mapped_column(Numeric(7, 2), nullable=False, default=0.0)
    form_settings: Mapped[dict[str, Any]] = mapped_column("settings", JSON, default=dict)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="generated_forms")
    user: Mapped[User] = relationship("User", back_populates="generated_forms")


# ─── Export Record ────────────────────────────────────────────────────────────

class ExportRecord(Base):
    __tablename__ = "export_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf|docx|excel|csv|json|txt|moodle|quizizz|kahoot
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    download_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="export_records")
    user: Mapped[User] = relationship("User", back_populates="export_records")
