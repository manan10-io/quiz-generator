"""
google_forms.py — FastAPI router for /forms/* endpoints.
Calls the Google Forms API to create a real quiz in the user's account.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.models import GeneratedForm, Project, Question, User
from app.schemas.schemas import (
    GenerateFormRequest, GeneratedFormList, GeneratedFormOut,
)
from app.google.forms_api import google_forms_api
from app.google.drive_api import google_drive_api
from app.google.oauth import get_valid_access_token, GoogleOAuthError

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── POST /forms/generate ─────────────────────────────────────────────────────

@router.post("/generate", response_model=GeneratedFormOut, status_code=status.HTTP_201_CREATED)
async def generate_form(
    data: GenerateFormRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new Google Form quiz from the questions in the specified project.
    Requires the user's Google access token (stored during OAuth sign-in).
    """
    # Verify project ownership
    proj_r = await db.execute(
        select(Project).where(
            Project.id == data.project_id,
            Project.user_id == current_user.id,
        )
    )
    project = proj_r.scalar_one_or_none()
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    # Fetch questions in order
    q_r = await db.execute(
        select(Question)
        .where(Question.project_id == data.project_id)
        .order_by(Question.position)
    )
    questions = q_r.scalars().all()

    if not questions:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Project has no questions to generate a form from",
        )

    # Require the user's Google access token — automatically refreshed if
    # the stored token has expired or is close to expiring.
    try:
        access_token = await get_valid_access_token(current_user, db)
    except GoogleOAuthError as e:
        logger.warning("Google token refresh failed for user %s: %s", current_user.id, e)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Your Google access has expired and could not be refreshed. "
                "Please sign out and sign in again to grant Google Forms access."
            ),
        )

    try:
        form_result = await google_forms_api.create_quiz(
            title=data.title,
            description=data.description,
            questions=questions,
            settings={
                "quiz_mode": data.quiz_mode,
                "shuffle_questions": data.shuffle_questions,
                "shuffle_options": data.shuffle_options,
                "immediate_release": data.immediate_release,
                "confirmation_message": data.confirmation_message,
            },
            access_token=access_token,
        )
    except Exception as e:
        logger.error("Google Forms API error: %s", e, exc_info=True)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=f"Google Forms API error: {str(e)}",
        )

    # Best-effort: organize the new form into a dedicated Drive folder.
    # This is non-critical — the form already exists and is usable even if
    # folder placement fails (e.g. transient Drive API hiccup), so we log
    # and continue rather than failing the whole request.
    try:
        folder_id = await google_drive_api.ensure_folder(access_token)
        await google_drive_api.move_file_to_folder(
            access_token, form_result["form_id"], folder_id
        )
    except Exception as e:
        logger.warning(
            "Could not organize form %s into Drive folder: %s",
            form_result["form_id"], e,
        )

    total_marks = sum(float(q.marks) for q in questions)

    generated = GeneratedForm(
        project_id=data.project_id,
        user_id=current_user.id,
        google_form_id=form_result["form_id"],
        google_form_url=form_result["responder_url"],
        google_form_edit_url=form_result["edit_url"],
        title=data.title,
        description=data.description or None,
        question_count=len(questions),
        total_marks=total_marks,
        form_settings={
            "quiz_mode": data.quiz_mode,
            "shuffle_questions": data.shuffle_questions,
            "shuffle_options": data.shuffle_options,
            "immediate_release": data.immediate_release,
            "confirmation_message": data.confirmation_message,
        },
    )
    db.add(generated)
    await db.flush()
    return GeneratedFormOut.from_orm_form(generated)


# ─── GET /forms ───────────────────────────────────────────────────────────────

@router.get("", response_model=GeneratedFormList)
async def list_forms(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GeneratedForm)
        .where(GeneratedForm.user_id == current_user.id)
        .order_by(GeneratedForm.generated_at.desc())
        .limit(50)
    )
    forms = result.scalars().all()
    return GeneratedFormList(items=[GeneratedFormOut.from_orm_form(f) for f in forms])


# ─── GET /forms/{id} ──────────────────────────────────────────────────────────

@router.get("/{form_id}", response_model=GeneratedFormOut)
async def get_form(
    form_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GeneratedForm).where(
            GeneratedForm.id == form_id,
            GeneratedForm.user_id == current_user.id,
        )
    )
    form = result.scalar_one_or_none()
    if not form:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Form not found")
    return GeneratedFormOut.from_orm_form(form)


# ─── DELETE /forms/{id} ───────────────────────────────────────────────────────

@router.delete("/{form_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_form_record(
    form_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deletes the record from our DB. Does NOT delete the form in Google Drive."""
    result = await db.execute(
        select(GeneratedForm).where(
            GeneratedForm.id == form_id,
            GeneratedForm.user_id == current_user.id,
        )
    )
    form = result.scalar_one_or_none()
    if not form:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Form not found")
    await db.delete(form)
    return None
