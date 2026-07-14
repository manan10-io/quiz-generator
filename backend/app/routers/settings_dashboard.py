"""
settings.py + dashboard.py — Settings and stats endpoints.
Combined in one file since both are short.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.models import GeneratedForm, Project, Question, User
from app.schemas.schemas import (
    DashboardStats, DifficultyDistribution, TopicCount,
    UserOut, UserSettings, UserSettingsUpdate,
)
from app.services.auth_service import auth_service

# ─── Settings router ──────────────────────────────────────────────────────────

settings_router = APIRouter()


@settings_router.get("", response_model=UserSettings)
async def get_settings(current_user: User = Depends(get_current_user)):
    return UserSettings(**(current_user.settings or {}))


@settings_router.put("", response_model=UserSettings)
async def update_settings(
    data: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updates = data.model_dump(exclude_unset=True)
    user = await auth_service.update_settings(current_user, updates, db)
    return UserSettings(**(user.settings or {}))


# ─── Dashboard router ─────────────────────────────────────────────────────────

dashboard_router = APIRouter()


@dashboard_router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = current_user.id
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    # Total questions
    total_q = await db.execute(
        select(func.count(Question.id))
        .join(Project, Question.project_id == Project.id)
        .where(Project.user_id == user_id)
    )
    total_questions = total_q.scalar_one()

    # Total projects
    total_p = await db.execute(
        select(func.count(Project.id)).where(Project.user_id == user_id)
    )
    total_projects = total_p.scalar_one()

    # Forms generated
    total_f = await db.execute(
        select(func.count(GeneratedForm.id)).where(GeneratedForm.user_id == user_id)
    )
    forms_generated = total_f.scalar_one()

    # Questions this week
    week_q = await db.execute(
        select(func.count(Question.id))
        .join(Project, Question.project_id == Project.id)
        .where(Project.user_id == user_id, Question.created_at >= one_week_ago)
    )
    questions_this_week = week_q.scalar_one()

    # Difficulty distribution
    diff_r = await db.execute(
        select(Question.difficulty, func.count(Question.id))
        .join(Project, Question.project_id == Project.id)
        .where(Project.user_id == user_id, Question.difficulty.isnot(None))
        .group_by(Question.difficulty)
    )
    diff_rows = diff_r.all()
    diff_dist = DifficultyDistribution()
    for difficulty, count in diff_rows:
        if difficulty == "easy":
            diff_dist.easy = count
        elif difficulty == "medium":
            diff_dist.medium = count
        elif difficulty == "hard":
            diff_dist.hard = count

    # Top topics
    topic_r = await db.execute(
        select(Question.topic, func.count(Question.id).label("cnt"))
        .join(Project, Question.project_id == Project.id)
        .where(Project.user_id == user_id, Question.topic.isnot(None))
        .group_by(Question.topic)
        .order_by(func.count(Question.id).desc())
        .limit(10)
    )
    top_topics = [TopicCount(topic=row[0], count=row[1]) for row in topic_r.all()]

    # Parse accuracy estimate: % valid questions
    valid_r = await db.execute(
        select(func.count(Question.id))
        .join(Project, Question.project_id == Project.id)
        .where(Project.user_id == user_id, Question.is_valid == True)
    )
    valid_count = valid_r.scalar_one()
    accuracy = round((valid_count / total_questions) * 100) if total_questions else 100

    return DashboardStats(
        total_questions=total_questions,
        total_projects=total_projects,
        forms_generated=forms_generated,
        parse_accuracy=accuracy,
        questions_this_week=questions_this_week,
        difficulty_distribution=diff_dist,
        top_topics=top_topics,
    )
