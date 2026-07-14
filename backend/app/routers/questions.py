"""
questions.py — FastAPI router for /projects/{id}/questions/* endpoints.
All routes verify the requesting user owns the parent project.
"""
from __future__ import annotations

import logging
import math

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.models import Project, Question, User
from app.schemas.schemas import (
    QuestionCreate, QuestionList, QuestionOut, QuestionUpdate, ReorderRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_owned_project(
    project_id: str, user: User, db: AsyncSession
) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    if project.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Access denied")
    return project


async def _get_question(
    question_id: str, project_id: str, db: AsyncSession
) -> Question:
    result = await db.execute(
        select(Question).where(
            Question.id == question_id,
            Question.project_id == project_id,
        )
    )
    q = result.scalar_one_or_none()
    if q is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Question not found")
    return q


async def _update_project_count(project_id: str, db: AsyncSession) -> None:
    count_result = await db.execute(
        select(func.count()).where(Question.project_id == project_id)
    )
    count = count_result.scalar_one()
    await db.execute(
        update(Project)
        .where(Project.id == project_id)
        .values(question_count=count)
    )


# ─── GET /projects/{id}/questions ─────────────────────────────────────────────

@router.get("/{project_id}/questions", response_model=QuestionList)
async def list_questions(
    project_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_project(project_id, current_user, db)

    base_q = select(Question).where(Question.project_id == project_id)

    total_r = await db.execute(select(func.count()).select_from(base_q.subquery()))
    total = total_r.scalar_one()

    q = base_q.order_by(Question.position).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    questions = result.scalars().all()

    return QuestionList(
        items=[QuestionOut.model_validate(q) for q in questions],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


# ─── POST /projects/{id}/questions ────────────────────────────────────────────

@router.post(
    "/{project_id}/questions",
    response_model=QuestionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_question(
    project_id: str,
    data: QuestionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_project(project_id, current_user, db)

    question = Question(
        project_id=project_id,
        question_text=data.question_text,
        option_a=data.option_a,
        option_b=data.option_b,
        option_c=data.option_c,
        option_d=data.option_d,
        option_e=data.option_e,
        correct_answer=data.correct_answer,
        marks=data.marks,
        negative_marks=data.negative_marks,
        difficulty=data.difficulty,
        topic=data.topic,
        explanation=data.explanation,
        position=data.position,
    )
    db.add(question)
    await db.flush()
    await _update_project_count(project_id, db)
    return QuestionOut.model_validate(question)


# ─── PATCH /projects/{id}/questions/{qid} ────────────────────────────────────

@router.patch("/{project_id}/questions/{question_id}", response_model=QuestionOut)
async def update_question(
    project_id: str,
    question_id: str,
    data: QuestionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_project(project_id, current_user, db)
    question = await _get_question(question_id, project_id, db)

    # Apply only the provided fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(question, field, value)

    await db.flush()
    return QuestionOut.model_validate(question)


# ─── DELETE /projects/{id}/questions/{qid} ───────────────────────────────────

@router.delete(
    "/{project_id}/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_question(
    project_id: str,
    question_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_project(project_id, current_user, db)
    question = await _get_question(question_id, project_id, db)
    await db.delete(question)
    await db.flush()  # session has autoflush=False — the delete must be
    # flushed before the SELECT below, or it still returns the deleted row
    # and the renumbering loop leaves a gap in the surviving positions.

    # Re-number positions after delete
    remaining_r = await db.execute(
        select(Question)
        .where(Question.project_id == project_id)
        .order_by(Question.position)
    )
    for idx, q in enumerate(remaining_r.scalars().all()):
        q.position = idx

    await _update_project_count(project_id, db)
    return None


# ─── POST /projects/{id}/questions/{qid}/duplicate ───────────────────────────

@router.post(
    "/{project_id}/questions/{question_id}/duplicate",
    response_model=QuestionOut,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_question(
    project_id: str,
    question_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_project(project_id, current_user, db)
    original = await _get_question(question_id, project_id, db)

    # Shift positions of questions after the original to make room
    await db.execute(
        update(Question)
        .where(
            Question.project_id == project_id,
            Question.position > original.position,
        )
        .values(position=Question.position + 1)
    )

    clone = Question(
        project_id=project_id,
        question_number=original.question_number,
        question_text=original.question_text,
        option_a=original.option_a,
        option_b=original.option_b,
        option_c=original.option_c,
        option_d=original.option_d,
        option_e=original.option_e,
        correct_answer=original.correct_answer,
        marks=original.marks,
        negative_marks=original.negative_marks,
        difficulty=original.difficulty,
        topic=original.topic,
        explanation=original.explanation,
        position=original.position + 1,
        is_valid=original.is_valid,
        validation_errors=list(original.validation_errors or []),
    )
    db.add(clone)
    await db.flush()
    await _update_project_count(project_id, db)
    return QuestionOut.model_validate(clone)


# ─── POST /projects/{id}/questions/reorder ───────────────────────────────────

@router.post("/{project_id}/questions/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_questions(
    project_id: str,
    data: ReorderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Accepts an ordered list of question IDs and updates their position fields.
    The client optimistically applies the reorder; this endpoint persists it.
    """
    await _get_owned_project(project_id, current_user, db)

    for position, question_id in enumerate(data.ordered_ids):
        await db.execute(
            update(Question)
            .where(Question.id == question_id, Question.project_id == project_id)
            .values(position=position)
        )
    return None


# ─── POST /projects/{id}/questions/validate ──────────────────────────────────

@router.post("/{project_id}/questions/validate")
async def validate_questions(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-run validation on all questions in the project and update their status."""
    await _get_owned_project(project_id, current_user, db)

    from app.parser.validator import validator
    from app.schemas.parser import ParsedQuestion

    result = await db.execute(
        select(Question).where(Question.project_id == project_id).order_by(Question.position)
    )
    questions = result.scalars().all()

    # Convert ORM objects to ParsedQuestion for the validator
    parsed = [
        ParsedQuestion(
            id=q.id,
            question_text=q.question_text,
            option_a=q.option_a or "",
            option_b=q.option_b or "",
            option_c=q.option_c or "",
            option_d=q.option_d or "",
            option_e=q.option_e or "",
            correct_answer=q.correct_answer,
            marks=float(q.marks),
            position=q.position,
        )
        for q in questions
    ]

    validated, global_warnings, _ = validator.validate_all(parsed, remove_duplicates=False)

    # Write validation results back to the DB
    for i, (orm_q, parsed_q) in enumerate(zip(questions, validated)):
        orm_q.is_valid = parsed_q.is_valid
        orm_q.validation_errors = parsed_q.validation_errors

    await db.flush()

    valid_count = sum(1 for q in validated if q.is_valid)
    invalid_count = len(validated) - valid_count

    return {
        "valid": valid_count,
        "invalid": invalid_count,
        "warnings": global_warnings,
    }
