"""
export_cleanup.py — Reclaims disk space and pruned DB rows for expired exports.

Signed download tokens already fail closed once expired (see signed_url.py),
so this module is purely about housekeeping — deleting the on-disk files and
their ExportRecord rows once they're no longer downloadable, so temp storage
doesn't grow unbounded.

Designed to be called two ways:
  1. Periodically from a background task (see main.py lifespan) in production.
  2. On-demand via a manual admin trigger, or directly in tests.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import ExportRecord

logger = logging.getLogger(__name__)


async def cleanup_expired_exports(db: AsyncSession, export_dir: Path) -> dict:
    """
    Deletes expired ExportRecord rows and their corresponding on-disk files.

    Returns a summary dict: {"records_deleted": int, "files_deleted": int,
    "files_missing": int} — the last count tracks records whose file was
    already gone from disk (not an error, just informational).
    """
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(ExportRecord).where(
            ExportRecord.expires_at.isnot(None),
            ExportRecord.expires_at < now,
        )
    )
    expired_records = result.scalars().all()

    files_deleted = 0
    files_missing = 0

    for record in expired_records:
        file_path = export_dir / f"{record.id}__{record.file_name}"
        if file_path.exists():
            try:
                file_path.unlink()
                files_deleted += 1
            except OSError as e:
                logger.warning("Could not delete export file %s: %s", file_path, e)
        else:
            files_missing += 1

        await db.delete(record)

    await db.flush()

    logger.info(
        "Export cleanup: removed %d record(s), deleted %d file(s), %d already missing",
        len(expired_records), files_deleted, files_missing,
    )

    return {
        "records_deleted": len(expired_records),
        "files_deleted": files_deleted,
        "files_missing": files_missing,
    }
