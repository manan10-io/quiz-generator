"""
drive_api.py — Google Drive API v3 client for organizing generated forms.

Without this, every quiz a user generates lands loose in their Drive root,
which gets unmanageable fast for a teacher generating dozens of quizzes.
This module finds-or-creates a single "QuizGen AI Quizzes" folder in the
user's Drive and moves each newly-created form into it.

Uses the REST API directly via httpx (same pattern as forms_api.py) rather
than the heavy google-api-python-client, keeping the dependency footprint
small and the calls easy to test/mock.
"""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

DRIVE_FILES_API = "https://www.googleapis.com/drive/v3/files"
DEFAULT_FOLDER_NAME = "QuizGen AI Quizzes"
GOOGLE_FOLDER_MIME = "application/vnd.google-apps.folder"


class GoogleDriveAPI:
    """Async Google Drive API client for folder management."""

    def _auth_headers(self, access_token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def ensure_folder(
        self,
        access_token: str,
        folder_name: str = DEFAULT_FOLDER_NAME,
    ) -> str:
        """
        Finds the QuizGen folder in the user's Drive, creating it if it
        doesn't exist yet. Returns the folder's file ID.

        Idempotent: safe to call before every form generation — subsequent
        calls will find the existing folder rather than creating duplicates.
        """
        headers = self._auth_headers(access_token)

        async with httpx.AsyncClient(timeout=20.0) as client:
            existing_id = await self._find_folder(client, headers, folder_name)
            if existing_id:
                return existing_id
            return await self._create_folder(client, headers, folder_name)

    async def move_file_to_folder(
        self,
        access_token: str,
        file_id: str,
        folder_id: str,
    ) -> None:
        """
        Moves a file (e.g. a newly-created Form) into the target folder.
        Google Drive's API models "move" as adding the new parent and
        removing the old one(s) in a single PATCH request.
        """
        headers = self._auth_headers(access_token)

        async with httpx.AsyncClient(timeout=20.0) as client:
            # First fetch current parents so we can remove them cleanly
            current_parents = await self._get_current_parents(client, headers, file_id)

            params = {"addParents": folder_id}
            if current_parents:
                params["removeParents"] = ",".join(current_parents)

            response = await client.patch(
                f"{DRIVE_FILES_API}/{file_id}",
                headers=headers,
                params=params,
                json={},
            )
            self._raise_for_status(response, "move file to folder")

    # ─── Internal helpers ─────────────────────────────────────────────────────

    async def _find_folder(
        self, client: httpx.AsyncClient, headers: dict, folder_name: str
    ) -> str | None:
        """Search for an existing, non-trashed folder with this exact name."""
        query = (
            f"name = '{self._escape(folder_name)}' "
            f"and mimeType = '{GOOGLE_FOLDER_MIME}' "
            f"and trashed = false"
        )
        response = await client.get(
            DRIVE_FILES_API,
            headers=headers,
            params={"q": query, "fields": "files(id, name)", "pageSize": 1},
        )
        self._raise_for_status(response, "search for folder")

        files = response.json().get("files", [])
        if files:
            logger.debug("Found existing Drive folder: %s", files[0]["id"])
            return files[0]["id"]
        return None

    async def _create_folder(
        self, client: httpx.AsyncClient, headers: dict, folder_name: str
    ) -> str:
        payload = {"name": folder_name, "mimeType": GOOGLE_FOLDER_MIME}
        response = await client.post(DRIVE_FILES_API, headers=headers, json=payload)
        self._raise_for_status(response, "create folder")

        folder_id = response.json()["id"]
        logger.info("Created new Drive folder '%s': %s", folder_name, folder_id)
        return folder_id

    async def _get_current_parents(
        self, client: httpx.AsyncClient, headers: dict, file_id: str
    ) -> list[str]:
        response = await client.get(
            f"{DRIVE_FILES_API}/{file_id}",
            headers=headers,
            params={"fields": "parents"},
        )
        self._raise_for_status(response, "fetch file parents")
        return response.json().get("parents", [])

    def _escape(self, value: str) -> str:
        """Escape single quotes for safe inclusion in a Drive query string."""
        return value.replace("'", "\\'")

    def _raise_for_status(self, response: httpx.Response, operation: str) -> None:
        if response.status_code >= 400:
            try:
                detail = response.json().get("error", {}).get("message", response.text[:200])
            except Exception:
                detail = response.text[:200]
            raise RuntimeError(
                f"Google Drive API {operation} failed "
                f"({response.status_code}): {detail}"
            )


# ─── Singleton ────────────────────────────────────────────────────────────────
google_drive_api = GoogleDriveAPI()
