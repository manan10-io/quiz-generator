"""
dependencies.py — FastAPI authentication dependency.

Usage in any protected router:

    from app.auth.dependencies import get_current_user
    from app.models.models import User

    @router.get("/something")
    async def endpoint(current_user: User = Depends(get_current_user)):
        ...

The dependency extracts the Bearer token from the Authorization header,
decodes it, fetches the User record from the database, and returns it.
Any missing/invalid/expired token raises HTTP 401.
"""
from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import User
from app.auth.jwt_utils import decode_access_token

logger = logging.getLogger(__name__)

# HTTPBearer extracts the token from the "Authorization: Bearer <token>" header
_bearer_scheme = HTTPBearer(auto_error=False)

_401 = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency: validate JWT and return the authenticated User ORM object.
    Raises HTTP 401 if the token is missing, invalid, or the user doesn't exist.
    """
    if credentials is None:
        raise _401

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except JWTError as e:
        logger.debug("JWT decode failed: %s", e)
        raise _401

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise _401

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        # Token was valid but user was deleted from DB
        raise _401

    return user


# ─── Optional auth (does not raise on missing token) ─────────────────────────

async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Like get_current_user but returns None instead of raising 401.
    Useful for endpoints that serve both authenticated and anonymous users.
    """
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials=credentials, db=db)
    except HTTPException:
        return None
