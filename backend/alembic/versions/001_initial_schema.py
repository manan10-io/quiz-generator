"""initial schema — users, projects, questions, parse_jobs, generated_forms, export_records

Revision ID: 001
Revises:
Create Date: 2026-01-15 00:00:00.000000

Hand-written to mirror app/models/models.py exactly, since Alembic isn't
installed in the sandbox this project was authored in to run --autogenerate.
Column types, nullability, defaults, and indexes match the ORM definitions
field-for-field — cross-check against models.py if the two ever drift.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("google_id", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("google_access_token", sa.Text(), nullable=True),
        sa.Column("google_refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_google_id", "users", ["google_id"])

    # ─── projects ───────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("question_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_projects_user_updated", "projects", ["user_id", "updated_at"])
    op.create_index("ix_projects_status", "projects", ["status"])

    # ─── questions ──────────────────────────────────────────────────────────
    op.create_table(
        "questions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_number", sa.Integer(), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("option_a", sa.Text(), nullable=False, server_default=""),
        sa.Column("option_b", sa.Text(), nullable=False, server_default=""),
        sa.Column("option_c", sa.Text(), nullable=False, server_default=""),
        sa.Column("option_d", sa.Text(), nullable=False, server_default=""),
        sa.Column("option_e", sa.Text(), nullable=False, server_default=""),
        sa.Column("correct_answer", sa.String(5), nullable=True),
        sa.Column("marks", sa.Numeric(5, 2), nullable=False, server_default="1.0"),
        sa.Column("negative_marks", sa.Numeric(5, 2), nullable=False, server_default="0.0"),
        sa.Column("difficulty", sa.String(10), nullable=True),
        sa.Column("topic", sa.String(255), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_valid", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("validation_errors", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_questions_project_position", "questions", ["project_id", "position"])
    op.create_index("ix_questions_topic", "questions", ["topic"])
    op.create_index("ix_questions_difficulty", "questions", ["difficulty"])
    op.create_index("ix_questions_valid", "questions", ["is_valid"])

    # ─── parse_jobs ─────────────────────────────────────────────────────────
    op.create_table(
        "parse_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("input_type", sa.String(20), nullable=False, server_default="text"),
        sa.Column("original_text", sa.Text(), nullable=True),
        sa.Column("cleaned_text", sa.Text(), nullable=True),
        sa.Column("questions_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ─── generated_forms ────────────────────────────────────────────────────
    op.create_table(
        "generated_forms",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("google_form_id", sa.String(255), nullable=False),
        sa.Column("google_form_url", sa.Text(), nullable=False),
        sa.Column("google_form_edit_url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("question_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_marks", sa.Numeric(7, 2), nullable=False, server_default="0.0"),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ─── export_records ─────────────────────────────────────────────────────
    op.create_table(
        "export_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format", sa.String(20), nullable=False),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("download_url", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    # Drop in reverse dependency order (children before parents)
    op.drop_table("export_records")
    op.drop_table("generated_forms")
    op.drop_table("parse_jobs")
    op.drop_index("ix_questions_valid", table_name="questions")
    op.drop_index("ix_questions_difficulty", table_name="questions")
    op.drop_index("ix_questions_topic", table_name="questions")
    op.drop_index("ix_questions_project_position", table_name="questions")
    op.drop_table("questions")
    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_index("ix_projects_user_updated", table_name="projects")
    op.drop_table("projects")
    op.drop_index("ix_users_google_id", table_name="users")
    op.drop_table("users")
