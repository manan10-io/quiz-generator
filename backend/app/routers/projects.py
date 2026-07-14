"""
projects.py — FastAPI router for /projects/* endpoints.
All routes require authentication via JWT.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.models import Project, Question, User
from app.schemas.schemas import (
    ProjectCreate, ProjectList, ProjectOut, ProjectUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _project_or_404(project: Project | None, project_id: str) -> Project:
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return project


def _assert_owner(project: Project, user: User) -> None:
    if project.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this project",
        )


# ─── GET /projects ────────────────────────────────────────────────────────────

@router.get("", response_model=ProjectList)
async def list_projects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Project).where(Project.user_id == current_user.id)
    if status_filter:
        q = q.where(Project.status == status_filter)
    q = q.order_by(Project.updated_at.desc())

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()

    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    projects = result.scalars().all()

    return ProjectList(
        items=[ProjectOut.from_orm_project(p) for p in projects],
        total=total,
    )


# ─── POST /projects ───────────────────────────────────────────────────────────

@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = Project(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
    )
    db.add(project)
    await db.flush()
    return ProjectOut.from_orm_project(project)


# ─── GET /projects/{id} ───────────────────────────────────────────────────────

@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = _project_or_404(result.scalar_one_or_none(), project_id)
    _assert_owner(project, current_user)
    return ProjectOut.from_orm_project(project)


# ─── PATCH /projects/{id} ─────────────────────────────────────────────────────

@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = _project_or_404(result.scalar_one_or_none(), project_id)
    _assert_owner(project, current_user)

    if data.name is not None:
        project.name = data.name
    if data.description is not None:
        project.description = data.description
    if data.status is not None:
        project.status = data.status

    await db.flush()
    return ProjectOut.from_orm_project(project)


# ─── DELETE /projects/{id} ────────────────────────────────────────────────────

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = _project_or_404(result.scalar_one_or_none(), project_id)
    _assert_owner(project, current_user)
    await db.delete(project)
    return None


# ─── POST /projects/{id}/duplicate ───────────────────────────────────────────

@router.post("/{project_id}/duplicate", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def duplicate_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    original = _project_or_404(result.scalar_one_or_none(), project_id)
    _assert_owner(original, current_user)

    # Create a new project with the same name (suffixed "Copy")
    clone = Project(
        user_id=current_user.id,
        name=f"{original.name} (Copy)",
        description=original.description,
        status="draft",
    )
    db.add(clone)
    await db.flush()

    # Duplicate all questions
    q_result = await db.execute(
        select(Question)
        .where(Question.project_id == project_id)
        .order_by(Question.position)
    )
    original_questions = q_result.scalars().all()

    for orig_q in original_questions:
        new_q = Question(
            project_id=clone.id,
            question_number=orig_q.question_number,
            question_text=orig_q.question_text,
            option_a=orig_q.option_a,
            option_b=orig_q.option_b,
            option_c=orig_q.option_c,
            option_d=orig_q.option_d,
            option_e=orig_q.option_e,
            correct_answer=orig_q.correct_answer,
            marks=orig_q.marks,
            negative_marks=orig_q.negative_marks,
            difficulty=orig_q.difficulty,
            topic=orig_q.topic,
            explanation=orig_q.explanation,
            position=orig_q.position,
            is_valid=orig_q.is_valid,
            validation_errors=list(orig_q.validation_errors or []),
        )
        db.add(new_q)

    clone.question_count = len(original_questions)
    await db.flush()
    return ProjectOut.from_orm_project(clone)
