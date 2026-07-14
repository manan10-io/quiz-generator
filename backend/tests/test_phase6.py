"""
test_phase6.py — Google OAuth token refresh + Drive API folder organization.

Uses a scriptable fake httpx.AsyncClient so these tests exercise the real
business logic (expiry math, query construction, parent-diffing for moves)
without making live calls to Google.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
import httpx

from app.google.oauth import (
    is_token_expired,
    refresh_access_token,
    get_valid_access_token,
    GoogleOAuthError,
)
from app.google.drive_api import GoogleDriveAPI, DEFAULT_FOLDER_NAME, GOOGLE_FOLDER_MIME
from app.models.models import User


# ─── Fake httpx transport ──────────────────────────────────────────────────────

class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text or str(json_data)

    def json(self):
        return self._json


class FakeAsyncClient:
    """Records every call made and returns pre-scripted responses in order."""

    script: list[FakeResponse] = []
    calls: list[tuple[str, str, dict]] = []

    def __init__(self, timeout=None):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    async def post(self, url, **kwargs):
        FakeAsyncClient.calls.append(("POST", url, kwargs))
        return FakeAsyncClient.script.pop(0)

    async def get(self, url, **kwargs):
        FakeAsyncClient.calls.append(("GET", url, kwargs))
        return FakeAsyncClient.script.pop(0)

    async def patch(self, url, **kwargs):
        FakeAsyncClient.calls.append(("PATCH", url, kwargs))
        return FakeAsyncClient.script.pop(0)


@pytest.fixture(autouse=True)
def patch_httpx(monkeypatch):
    """Replace httpx.AsyncClient with our fake for every test in this module."""
    FakeAsyncClient.script = []
    FakeAsyncClient.calls = []
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    yield


@pytest.fixture
def fake_db():
    class FakeDB:
        def __init__(self):
            self.flushed = False

        async def flush(self):
            self.flushed = True

    return FakeDB()


# ─── is_token_expired ──────────────────────────────────────────────────────────

class TestIsTokenExpired:

    def test_none_expiry_is_expired(self):
        assert is_token_expired(None) is True

    def test_past_expiry_is_expired(self):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        assert is_token_expired(past) is True

    def test_far_future_not_expired(self):
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        assert is_token_expired(future) is False

    def test_within_safety_margin_is_expired(self):
        """Tokens expiring within 5 minutes should be treated as expired."""
        soon = datetime.now(timezone.utc) + timedelta(minutes=2)
        assert is_token_expired(soon) is True

    def test_just_outside_margin_not_expired(self):
        later = datetime.now(timezone.utc) + timedelta(minutes=10)
        assert is_token_expired(later) is False

    def test_naive_datetime_does_not_crash(self):
        """Timezone-naive datetimes should be handled gracefully."""
        naive_future = datetime.now() + timedelta(hours=2)
        assert is_token_expired(naive_future) is False


# ─── refresh_access_token ──────────────────────────────────────────────────────

class TestRefreshAccessToken:

    @pytest.mark.asyncio
    async def test_returns_new_access_token(self):
        FakeAsyncClient.script = [
            FakeResponse(200, {"access_token": "new-tok", "expires_in": 3600})
        ]
        result = await refresh_access_token("my-refresh-token")
        assert result["access_token"] == "new-tok"
        assert result["expires_in"] == 3600

    @pytest.mark.asyncio
    async def test_posts_to_google_token_endpoint(self):
        FakeAsyncClient.script = [FakeResponse(200, {"access_token": "t", "expires_in": 3600})]
        await refresh_access_token("rt")
        assert FakeAsyncClient.calls[0][1] == "https://oauth2.googleapis.com/token"

    @pytest.mark.asyncio
    async def test_sends_refresh_token_and_grant_type(self):
        FakeAsyncClient.script = [FakeResponse(200, {"access_token": "t", "expires_in": 3600})]
        await refresh_access_token("my-specific-token")
        payload = FakeAsyncClient.calls[0][2]["data"]
        assert payload["refresh_token"] == "my-specific-token"
        assert payload["grant_type"] == "refresh_token"

    @pytest.mark.asyncio
    async def test_raises_on_revoked_token(self):
        FakeAsyncClient.script = [
            FakeResponse(400, {"error": "invalid_grant", "error_description": "Token has been revoked"})
        ]
        with pytest.raises(GoogleOAuthError, match="revoked"):
            await refresh_access_token("revoked-token")

    @pytest.mark.asyncio
    async def test_raises_on_network_error(self):
        class BrokenClient(FakeAsyncClient):
            async def post(self, url, **kwargs):
                raise httpx.RequestError("connection failed")

        import httpx as httpx_mod
        original = httpx_mod.AsyncClient
        httpx_mod.AsyncClient = BrokenClient
        try:
            with pytest.raises(GoogleOAuthError, match="Network error"):
                await refresh_access_token("rt")
        finally:
            httpx_mod.AsyncClient = original


# ─── get_valid_access_token ────────────────────────────────────────────────────

class TestGetValidAccessToken:

    @pytest.mark.asyncio
    async def test_returns_fresh_token_without_network_call(self, fake_db):
        user = User()
        user.google_access_token = "still-good"
        user.token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        token = await get_valid_access_token(user, fake_db)

        assert token == "still-good"
        assert len(FakeAsyncClient.calls) == 0
        assert fake_db.flushed is False

    @pytest.mark.asyncio
    async def test_refreshes_expired_token(self, fake_db):
        user = User()
        user.google_access_token = "old-tok"
        user.google_refresh_token = "refresh-abc"
        user.token_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        FakeAsyncClient.script = [
            FakeResponse(200, {"access_token": "brand-new-tok", "expires_in": 3600})
        ]

        token = await get_valid_access_token(user, fake_db)

        assert token == "brand-new-tok"
        assert user.google_access_token == "brand-new-tok"

    @pytest.mark.asyncio
    async def test_updates_expiry_on_refresh(self, fake_db):
        user = User()
        user.google_refresh_token = "rt"
        user.token_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        FakeAsyncClient.script = [FakeResponse(200, {"access_token": "t", "expires_in": 3600})]
        await get_valid_access_token(user, fake_db)

        assert user.token_expires_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_persists_via_db_flush(self, fake_db):
        user = User()
        user.google_refresh_token = "rt"
        user.token_expires_at = None

        FakeAsyncClient.script = [FakeResponse(200, {"access_token": "t", "expires_in": 3600})]
        await get_valid_access_token(user, fake_db)

        assert fake_db.flushed is True

    @pytest.mark.asyncio
    async def test_raises_when_no_refresh_token(self, fake_db):
        user = User()
        user.google_access_token = "old-tok"
        user.google_refresh_token = None
        user.token_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        with pytest.raises(GoogleOAuthError, match="refresh token"):
            await get_valid_access_token(user, fake_db)


# ─── GoogleDriveAPI.ensure_folder ──────────────────────────────────────────────

class TestEnsureFolder:

    @pytest.mark.asyncio
    async def test_finds_existing_folder(self):
        api = GoogleDriveAPI()
        FakeAsyncClient.script = [
            FakeResponse(200, {"files": [{"id": "existing-id", "name": DEFAULT_FOLDER_NAME}]})
        ]
        folder_id = await api.ensure_folder("tok")
        assert folder_id == "existing-id"
        assert len(FakeAsyncClient.calls) == 1

    @pytest.mark.asyncio
    async def test_search_query_filters_by_mimetype_and_trashed(self):
        api = GoogleDriveAPI()
        FakeAsyncClient.script = [FakeResponse(200, {"files": [{"id": "x"}]})]
        await api.ensure_folder("tok")
        query = FakeAsyncClient.calls[0][2]["params"]["q"]
        assert GOOGLE_FOLDER_MIME in query
        assert "trashed = false" in query

    @pytest.mark.asyncio
    async def test_creates_folder_when_not_found(self):
        api = GoogleDriveAPI()
        FakeAsyncClient.script = [
            FakeResponse(200, {"files": []}),
            FakeResponse(200, {"id": "new-folder-id"}),
        ]
        folder_id = await api.ensure_folder("tok")
        assert folder_id == "new-folder-id"
        assert len(FakeAsyncClient.calls) == 2
        assert FakeAsyncClient.calls[1][0] == "POST"

    @pytest.mark.asyncio
    async def test_create_payload_has_correct_name_and_mimetype(self):
        api = GoogleDriveAPI()
        FakeAsyncClient.script = [
            FakeResponse(200, {"files": []}),
            FakeResponse(200, {"id": "new-id"}),
        ]
        await api.ensure_folder("tok")
        payload = FakeAsyncClient.calls[1][2]["json"]
        assert payload["name"] == DEFAULT_FOLDER_NAME
        assert payload["mimeType"] == GOOGLE_FOLDER_MIME

    @pytest.mark.asyncio
    async def test_custom_folder_name_respected(self):
        api = GoogleDriveAPI()
        FakeAsyncClient.script = [FakeResponse(200, {"files": [{"id": "x"}]})]
        await api.ensure_folder("tok", folder_name="My Custom Folder")
        assert "My Custom Folder" in FakeAsyncClient.calls[0][2]["params"]["q"]

    @pytest.mark.asyncio
    async def test_idempotent_second_call_reuses_folder(self):
        """Calling ensure_folder twice should not create duplicate folders."""
        api = GoogleDriveAPI()
        FakeAsyncClient.script = [
            FakeResponse(200, {"files": [{"id": "same-id"}]}),
            FakeResponse(200, {"files": [{"id": "same-id"}]}),
        ]
        id1 = await api.ensure_folder("tok")
        id2 = await api.ensure_folder("tok")
        assert id1 == id2 == "same-id"


# ─── GoogleDriveAPI.move_file_to_folder ────────────────────────────────────────

class TestMoveFileToFolder:

    @pytest.mark.asyncio
    async def test_fetches_parents_then_patches(self):
        api = GoogleDriveAPI()
        FakeAsyncClient.script = [
            FakeResponse(200, {"parents": ["old-parent"]}),
            FakeResponse(200, {"id": "file-1"}),
        ]
        await api.move_file_to_folder("tok", "file-1", "new-folder")
        assert FakeAsyncClient.calls[0][0] == "GET"
        assert FakeAsyncClient.calls[1][0] == "PATCH"

    @pytest.mark.asyncio
    async def test_add_and_remove_parents_correct(self):
        api = GoogleDriveAPI()
        FakeAsyncClient.script = [
            FakeResponse(200, {"parents": ["old-parent-id"]}),
            FakeResponse(200, {"id": "file-1"}),
        ]
        await api.move_file_to_folder("tok", "file-1", "new-folder-id")
        params = FakeAsyncClient.calls[1][2]["params"]
        assert params["addParents"] == "new-folder-id"
        assert params["removeParents"] == "old-parent-id"

    @pytest.mark.asyncio
    async def test_no_remove_parents_when_file_has_none(self):
        """A file with no existing parents shouldn't send removeParents."""
        api = GoogleDriveAPI()
        FakeAsyncClient.script = [
            FakeResponse(200, {}),  # no "parents" key
            FakeResponse(200, {"id": "file-2"}),
        ]
        await api.move_file_to_folder("tok", "file-2", "folder-x")
        params = FakeAsyncClient.calls[1][2]["params"]
        assert "removeParents" not in params
        assert params["addParents"] == "folder-x"


# ─── Error handling ─────────────────────────────────────────────────────────────

class TestDriveErrorHandling:

    @pytest.mark.asyncio
    async def test_raises_runtime_error_on_403(self):
        api = GoogleDriveAPI()
        FakeAsyncClient.script = [
            FakeResponse(403, {"error": {"message": "Insufficient permissions"}})
        ]
        with pytest.raises(RuntimeError, match="403"):
            await api.ensure_folder("bad-tok")

    @pytest.mark.asyncio
    async def test_error_message_includes_operation_context(self):
        api = GoogleDriveAPI()
        FakeAsyncClient.script = [
            FakeResponse(500, {"error": {"message": "Internal error"}})
        ]
        with pytest.raises(RuntimeError, match="search for folder"):
            await api.ensure_folder("tok")


# ─── Query string escaping ──────────────────────────────────────────────────────

class TestQueryEscaping:

    def test_escapes_single_quotes(self):
        api = GoogleDriveAPI()
        assert api._escape("Teacher's Quizzes") == "Teacher\\'s Quizzes"

    def test_no_change_when_no_quotes(self):
        api = GoogleDriveAPI()
        assert api._escape("Plain Folder Name") == "Plain Folder Name"
