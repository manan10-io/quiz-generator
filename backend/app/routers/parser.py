"""
parser.py — FastAPI router for /parse/* endpoints.

Routes:
  POST /parse/text       — Parse pasted text and persist questions (synchronous)
  POST /parse/file       — Upload a file, parse it, and persist questions (job)
  GET  /parse/jobs/{id}  — Poll job status

Both parse endpoints require authentication and a project the caller owns.
The extracted questions are written to the `questions` table so that every
downstream feature (editor, export, Google Forms, dashboard) sees them — the
parse response itself returns the freshly-persisted rows (with real ids).
"""

import json
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.models import Project, Question, User
from app.schemas.parser import (
    ParseTextRequest, ParseOptions, ParseJobStatus, ParseResult, ParsedQuestion,
)
from app.schemas.schemas import ParsePersistResult, QuestionOut
from app.services.parser_service import parser_service
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── In-memory job store (replace with Redis in production) ───────────────────
_jobs: dict[str, ParseJobStatus] = {}


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_owned_project(project_id: str, user: User, db: AsyncSession) -> Project:
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A project_id is required to parse into.",
        )
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    if project.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Access denied")
    return project


async def _persist_parsed_questions(
    db: AsyncSession,
    project: Project,
    parsed: list[ParsedQuestion],
    result: ParseResult,
    options: ParseOptions,
    source_type: str,
) -> list[Question]:
    """
    Write the parsed questions into the DB under `project`, appending after any
    existing questions, and refresh the project's question_count + metadata.
    Returns the newly-created Question ORM rows in order.
    """
    # Append after whatever is already in the project (supports re-parsing /
    # pasting additional batches into an existing project).
    count_r = await db.execute(
        select(func.count()).where(Question.project_id == project.id)
    )
    base = count_r.scalar_one()

    created: list[Question] = []
    for offset, pq in enumerate(parsed):
        position = base + offset
        question_number = position + 1 if options.auto_number else pq.question_number
        q = Question(
            project_id=project.id,
            question_number=question_number,
            question_text=pq.question_text,
            option_a=pq.option_a or "",
            option_b=pq.option_b or "",
            option_c=pq.option_c or "",
            option_d=pq.option_d or "",
            option_e=pq.option_e or "",
            correct_answer=pq.correct_answer,
            marks=pq.marks,
            negative_marks=pq.negative_marks,
            difficulty=pq.difficulty,
            topic=pq.topic,
            explanation=pq.explanation,
            position=position,
            is_valid=pq.is_valid,
            validation_errors=list(pq.validation_errors or []),
        )
        db.add(q)
        created.append(q)

    await db.flush()

    # Refresh denormalised project fields
    total_r = await db.execute(
        select(func.count()).where(Question.project_id == project.id)
    )
    project.question_count = total_r.scalar_one()

    topics = sorted({q.topic for q in created if q.topic})
    diff_dist = {"easy": 0, "medium": 0, "hard": 0}
    for q in created:
        if q.difficulty in diff_dist:
            diff_dist[q.difficulty] += 1

    project.metadata_ = {
        **(project.metadata_ or {}),
        "source_type": source_type,
        "topics_detected": topics,
        "difficulty_distribution": diff_dist,
        "warnings": result.warnings,
        "duplicates_found": result.duplicates_removed,
        "parse_duration_ms": result.parse_duration_ms,
    }
    if project.status == "draft" and project.question_count > 0:
        project.status = "ready"

    await db.flush()
    return created


# ─── POST /parse/text ────────────────────────────────────────────────────────

@router.post("/text", response_model=ParsePersistResult)
async def parse_text(
    request: ParseTextRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Parse pasted MCQ text synchronously and persist the questions."""
    if len(request.text) < 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Input text is too short to contain questions",
        )
    if len(request.text) > 500_000:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Text exceeds 500,000 character limit",
        )

    project = await _get_owned_project(request.project_id, current_user, db)
    job_id = str(uuid.uuid4())

    try:
        result = parser_service.parse_text(
            raw_text=request.text, options=request.options, job_id=job_id,
        )
    except Exception as e:
        logger.error("Text parse failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Parsing failed: {str(e)}",
        )

    created = await _persist_parsed_questions(
        db, project, result.questions, result, request.options, source_type="text",
    )

    return ParsePersistResult(
        job_id=job_id,
        questions=[QuestionOut.model_validate(q) for q in created],
        warnings=result.warnings,
        duplicates_removed=result.duplicates_removed,
        parse_duration_ms=result.parse_duration_ms,
        total_found=len(created),
        format_detected=result.format_detected,
    )


# ─── POST /parse/file ────────────────────────────────────────────────────────

@router.post("/file")
async def parse_file(
    file: UploadFile = File(...),
    project_id: str = Form(default=""),
    options: str = Form(default="{}"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a file (PDF, DOCX, TXT, CSV, image), parse it, and persist questions.
    Returns a job_id the frontend polls; because parsing runs inline the job is
    already complete by the time this returns.
    """
    project = await _get_owned_project(project_id, current_user, db)

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.MAX_UPLOAD_MB}MB limit",
        )

    try:
        options_dict = json.loads(options) if options else {}
        parse_opts = ParseOptions(**options_dict)
    except Exception:
        parse_opts = ParseOptions()

    job_id = str(uuid.uuid4())
    filename = file.filename or "upload.bin"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    source_type = ext if ext in ("pdf", "docx", "txt", "csv") else "image"

    _jobs[job_id] = ParseJobStatus(
        job_id=job_id, status="parsing", progress=40,
        message="Extracting and parsing questions…",
    )

    try:
        result = parser_service.parse_file(
            file_bytes=content, filename=filename, options=parse_opts, job_id=job_id,
        )

        created = await _persist_parsed_questions(
            db, project, result.questions, result, parse_opts, source_type=source_type,
        )

        _jobs[job_id] = ParseJobStatus(
            job_id=job_id, status="done", progress=100,
            message=f"Found {len(created)} questions",
            questions_found=len(created), warnings=result.warnings,
        )

        return {
            "job_id": job_id,
            "status": "done",
            "questions": [QuestionOut.model_validate(q).model_dump(mode="json") for q in created],
            "warnings": result.warnings,
            "duplicates_removed": result.duplicates_removed,
            "parse_duration_ms": result.parse_duration_ms,
            "format_detected": result.format_detected,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("File parse failed: %s", e, exc_info=True)
        _jobs[job_id] = ParseJobStatus(
            job_id=job_id, status="failed", progress=0,
            message="Parsing failed", error_message=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File parsing failed: {str(e)}",
        )


# ─── GET /parse/jobs/{job_id} ────────────────────────────────────────────────

@router.get("/jobs/{job_id}", response_model=ParseJobStatus)
async def get_job_status(job_id: str):
    """Poll the status of an async parse job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )
    return job
