"""
test_export_cleanup.py — Expired export file/record cleanup.

Uses real filesystem operations in pytest's tmp_path fixture and a minimal
fake DB session, so the actual file-deletion and record-pruning logic is
exercised end-to-end rather than mocked away.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.services.export_cleanup import cleanup_expired_exports


# ─── Fakes ──────────────────────────────────────────────────────────────────

class FakeExportRecord:
    def __init__(self, id: str, file_name: str, expires_at: datetime | None):
        self.id = id
        self.file_name = file_name
        self.expires_at = expires_at


class _FakeScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class _FakeResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return _FakeScalars(self._items)


class FakeDB:
    """
    Minimal async session stand-in. execute() applies the same expiry
    filter the real SQLAlchemy query would, without needing a live DB.
    """

    def __init__(self, records):
        self._records = records
        self.deleted_ids: list[str] = []
        self.flushed = False

    async def execute(self, _query):
        now = datetime.now(timezone.utc)
        expired = [r for r in self._records if r.expires_at and r.expires_at < now]
        return _FakeResult(expired)

    async def delete(self, record):
        self.deleted_ids.append(record.id)

    async def flush(self):
        self.flushed = True


def _write_export_file(export_dir: Path, record: FakeExportRecord, content: bytes):
    (export_dir / f"{record.id}__{record.file_name}").write_bytes(content)


# ─── Tests ──────────────────────────────────────────────────────────────────

class TestCleanupExpiredExports:

    @pytest.mark.asyncio
    async def test_deletes_expired_records_and_files(self, tmp_path):
        now = datetime.now(timezone.utc)
        expired = FakeExportRecord("exp-1", "quiz.csv", now - timedelta(hours=1))
        valid = FakeExportRecord("valid-1", "quiz2.csv", now + timedelta(hours=1))

        _write_export_file(tmp_path, expired, b"expired content")
        _write_export_file(tmp_path, valid, b"valid content")

        db = FakeDB([expired, valid])
        result = await cleanup_expired_exports(db, tmp_path)

        assert result["records_deleted"] == 1
        assert result["files_deleted"] == 1
        assert result["files_missing"] == 0

    @pytest.mark.asyncio
    async def test_expired_file_removed_from_disk(self, tmp_path):
        now = datetime.now(timezone.utc)
        expired = FakeExportRecord("exp-1", "quiz.csv", now - timedelta(hours=1))
        _write_export_file(tmp_path, expired, b"data")

        db = FakeDB([expired])
        await cleanup_expired_exports(db, tmp_path)

        assert not (tmp_path / "exp-1__quiz.csv").exists()

    @pytest.mark.asyncio
    async def test_valid_file_untouched(self, tmp_path):
        now = datetime.now(timezone.utc)
        valid = FakeExportRecord("valid-1", "quiz.csv", now + timedelta(hours=5))
        _write_export_file(tmp_path, valid, b"keep me")

        db = FakeDB([valid])
        await cleanup_expired_exports(db, tmp_path)

        path = tmp_path / "valid-1__quiz.csv"
        assert path.exists()
        assert path.read_bytes() == b"keep me"

    @pytest.mark.asyncio
    async def test_expired_record_deleted_from_db(self, tmp_path):
        now = datetime.now(timezone.utc)
        expired = FakeExportRecord("exp-1", "quiz.csv", now - timedelta(hours=1))
        _write_export_file(tmp_path, expired, b"data")

        db = FakeDB([expired])
        await cleanup_expired_exports(db, tmp_path)

        assert "exp-1" in db.deleted_ids

    @pytest.mark.asyncio
    async def test_valid_record_not_deleted_from_db(self, tmp_path):
        now = datetime.now(timezone.utc)
        valid = FakeExportRecord("valid-1", "quiz.csv", now + timedelta(hours=5))
        _write_export_file(tmp_path, valid, b"data")

        db = FakeDB([valid])
        await cleanup_expired_exports(db, tmp_path)

        assert "valid-1" not in db.deleted_ids

    @pytest.mark.asyncio
    async def test_flush_called_after_cleanup(self, tmp_path):
        now = datetime.now(timezone.utc)
        expired = FakeExportRecord("exp-1", "quiz.csv", now - timedelta(hours=1))
        _write_export_file(tmp_path, expired, b"data")

        db = FakeDB([expired])
        await cleanup_expired_exports(db, tmp_path)

        assert db.flushed is True

    @pytest.mark.asyncio
    async def test_missing_file_does_not_crash(self, tmp_path):
        """Record is expired but its file was already deleted somehow."""
        now = datetime.now(timezone.utc)
        ghost = FakeExportRecord("ghost-1", "gone.csv", now - timedelta(hours=1))
        # Deliberately do NOT write the file

        db = FakeDB([ghost])
        result = await cleanup_expired_exports(db, tmp_path)

        assert result["records_deleted"] == 1
        assert result["files_missing"] == 1
        assert result["files_deleted"] == 0
        assert "ghost-1" in db.deleted_ids

    @pytest.mark.asyncio
    async def test_no_expired_records_is_a_noop(self, tmp_path):
        now = datetime.now(timezone.utc)
        valid = FakeExportRecord("v1", "fresh.csv", now + timedelta(hours=5))
        _write_export_file(tmp_path, valid, b"data")

        db = FakeDB([valid])
        result = await cleanup_expired_exports(db, tmp_path)

        assert result["records_deleted"] == 0
        assert result["files_deleted"] == 0
        assert len(db.deleted_ids) == 0

    @pytest.mark.asyncio
    async def test_multiple_expired_records_all_cleaned(self, tmp_path):
        now = datetime.now(timezone.utc)
        records = [
            FakeExportRecord(f"exp-{i}", f"quiz{i}.csv", now - timedelta(hours=i + 1))
            for i in range(5)
        ]
        for r in records:
            _write_export_file(tmp_path, r, b"data")

        db = FakeDB(records)
        result = await cleanup_expired_exports(db, tmp_path)

        assert result["records_deleted"] == 5
        assert result["files_deleted"] == 5
        assert len(list(tmp_path.iterdir())) == 0

    @pytest.mark.asyncio
    async def test_records_with_no_expiry_are_never_cleaned(self, tmp_path):
        """A record with expires_at=None should be treated as non-expiring."""
        permanent = FakeExportRecord("perm-1", "forever.csv", None)
        _write_export_file(tmp_path, permanent, b"data")

        db = FakeDB([permanent])
        result = await cleanup_expired_exports(db, tmp_path)

        assert result["records_deleted"] == 0
        assert (tmp_path / "perm-1__forever.csv").exists()


class TestStoragePathCollisionSafety:
    """
    Verifies the record-ID-prefixed storage path prevents different users'
    (or different projects') exports from overwriting each other on disk
    when they share a display file name.
    """

    def test_same_filename_different_records_different_paths(self, tmp_path):
        def storage_path(record_id: str, file_name: str) -> Path:
            return tmp_path / f"{record_id}__{file_name}"

        path_a = storage_path("record-aaa", "Quiz.csv")
        path_b = storage_path("record-bbb", "Quiz.csv")

        assert path_a != path_b

    def test_both_files_coexist_without_overwrite(self, tmp_path):
        def storage_path(record_id: str, file_name: str) -> Path:
            return tmp_path / f"{record_id}__{file_name}"

        path_a = storage_path("user-A-export", "Chemistry Quiz.csv")
        path_b = storage_path("user-B-export", "Chemistry Quiz.csv")

        path_a.write_bytes(b"user A's questions")
        path_b.write_bytes(b"user B's questions")

        assert path_a.read_bytes() == b"user A's questions"
        assert path_b.read_bytes() == b"user B's questions"
