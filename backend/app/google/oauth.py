"""
oauth.py — Google OAuth2 token refresh handling.

Google access tokens expire after ~1 hour. The refresh_token obtained
during initial sign-in (with access_type=offline, prompt=consent — see
frontend lib/auth.ts) lets us silently obtain a new access_token without
asking the user to sign in again.

This module provides:
  - refresh_access_token()   — low-level token exchange with Google
  - get_valid_access_token() — high-level helper that checks expiry,
    refreshes if needed, persists the new token to the DB, and returns
    a token guaranteed usable for the next several minutes.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.models import User

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Refresh proactively if the token expires within this window, rather than
# waiting for it to fail mid-request against the Forms/Drive APIs.
REFRESH_SAFETY_MARGIN = timedelta(minutes=5)


class GoogleOAuthError(Exception):
    """Raised when Google's token endpoint rejects the refresh request."""


async def refresh_access_token(refresh_token: str) -> dict:
    """
    Exchange a refresh_token for a new access_token.

    Returns dict with keys: access_token, expires_in (seconds), token_type.
    Raises GoogleOAuthError on failure (e.g. refresh_token revoked by user).
    """
    payload = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(GOOGLE_TOKEN_URL, data=payload)
        except httpx.RequestError as e:
            raise GoogleOAuthError(f"Network error contacting Google: {e}") from e

    if response.status_code >= 400:
        try:
            detail = response.json().get("error_description", response.text[:200])
        except Exception:
            detail = response.text[:200]
        raise GoogleOAuthError(
            f"Google token refresh failed ({response.status_code}): {detail}"
        )

    return response.json()


def is_token_expired(expires_at: datetime | None) -> bool:
    """
    True if the token is missing an expiry, already expired, or expires
    within the safety margin — in all these cases a refresh is warranted.
    """
    if expires_at is None:
        return True
    now = datetime.now(timezone.utc)
    # Ensure expires_at is timezone-aware for comparison
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return now >= (expires_at - REFRESH_SAFETY_MARGIN)


async def get_valid_access_token(user: User, db: AsyncSession) -> str:
    """
    Returns a Google access token guaranteed to be valid for immediate use.

    If the stored token is still fresh, returns it as-is (no network call).
    If it's expired or close to expiring, refreshes it via Google's token
    endpoint and persists the new token + expiry back onto the user record.

    Raises GoogleOAuthError if no refresh_token is available or Google
    rejects the refresh (e.g. the user revoked access) — the caller should
    surface this as "please sign in again" to the frontend.
    """
    if not is_token_expired(user.token_expires_at) and user.google_access_token:
        return user.google_access_token

    if not user.google_refresh_token:
        raise GoogleOAuthError(
            "No refresh token on file. The user must sign in again to grant "
            "offline access (access_type=offline, prompt=consent)."
        )

    logger.info("Refreshing Google access token for user %s", user.id)
    token_data = await refresh_access_token(user.google_refresh_token)

    new_access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in", 3600)
    new_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    # Persist the refreshed token so subsequent requests reuse it
    user.google_access_token = new_access_token
    user.token_expires_at = new_expiry
    await db.flush()

    return new_access_token
