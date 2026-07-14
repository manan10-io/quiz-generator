"""
auth_service.py — Business logic for authentication.

Handles:
  - Receiving Google OAuth credentials from Next.js (after the browser OAuth
    flow completes on the frontend via NextAuth.js)
  - Upserting the User record (create on first sign-in, update on subsequent)
  - Issuing a short-lived JWT for the frontend to use on subsequent API calls
  - Optional token refresh
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone


def _expiry_to_datetime(expires_at: int | None) -> datetime | None:
    """Convert a Unix-seconds expiry (from Google via NextAuth) to a UTC datetime."""
    if not expires_at:
        return None
    try:
        return datetime.fromtimestamp(expires_at, tz=timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User
from app.schemas.schemas import GoogleAuthRequest, AuthResponse
from app.auth.jwt_utils import create_access_token

logger = logging.getLogger(__name__)


class AuthService:

    async def google_signin(
        self,
        data: GoogleAuthRequest,
        db: AsyncSession,
    ) -> AuthResponse:
        """
        Register or log in a user via their Google credentials.

        The frontend (NextAuth.js) has already completed the browser-side
        OAuth dance and verified the Google ID token. We receive the decoded
        claims and store/update the user record, then issue our own JWT.

        Returns an AuthResponse containing our JWT + basic user info.
        """
        # Try to find an existing user by Google ID (most common path)
        result = await db.execute(
            select(User).where(User.google_id == data.google_id)
        )
        user: User | None = result.scalar_one_or_none()

        if user is None:
            # First-ever sign-in for this Google account — create the record
            user = User(
                google_id=data.google_id,
                email=data.email,
                name=data.name,
                avatar_url=data.avatar_url,
                google_access_token=data.access_token,
                google_refresh_token=data.refresh_token,
                token_expires_at=_expiry_to_datetime(data.expires_at),
            )
            db.add(user)
            logger.info("New user registered: %s (%s)", data.email, data.google_id)
        else:
            # Returning user — refresh tokens and profile data
            user.name = data.name
            user.avatar_url = data.avatar_url
            if data.access_token:
                user.google_access_token = data.access_token
            if data.refresh_token:
                # Google only returns a refresh_token on first consent; never
                # clobber a stored one with None on subsequent sign-ins.
                user.google_refresh_token = data.refresh_token
            if data.expires_at:
                user.token_expires_at = _expiry_to_datetime(data.expires_at)
            logger.info("Existing user signed in: %s", data.email)

        await db.flush()  # Get the generated id without committing yet

        token = create_access_token(user_id=user.id, email=user.email)

        return AuthResponse(
            access_token=token,
            token_type="bearer",
            user_id=user.id,
            user_name=user.name,
            user_email=user.email,
            user_avatar=user.avatar_url,
        )

    async def get_user_by_id(self, user_id: str, db: AsyncSession) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_settings(
        self,
        user: User,
        updates: dict,
        db: AsyncSession,
    ) -> User:
        current = dict(user.settings or {})
        current.update(updates)
        user.settings = current
        await db.flush()
        return user


auth_service = AuthService()
