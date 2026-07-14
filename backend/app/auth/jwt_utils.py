"""
jwt_utils.py — JWT token generation and verification for the API.

Uses HS256 (HMAC-SHA256) signing with a secret key from settings.
Tokens carry user_id and email as claims. Expiry is configurable
(default 7 days via JWT_EXPIRE_MINUTES).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from app.config import settings


def create_access_token(
    user_id: str,
    email: str,
    extra_claims: dict | None = None,
) -> str:
    """
    Generate a signed JWT access token.

    Claims:
      sub   — user UUID (primary identity claim)
      email — user email (convenience for logging)
      exp   — expiry timestamp
      iat   — issued-at timestamp
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    payload: dict = {
        "sub": user_id,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT access token.

    Raises:
        JWTError — if the token is invalid, expired, or tampered with.
    Returns:
        The full decoded payload dict.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )


def extract_user_id(token: str) -> Optional[str]:
    """
    Convenience wrapper that returns just the user_id from a valid token,
    or None if decoding fails.
    """
    try:
        payload = decode_access_token(token)
        return payload.get("sub")
    except JWTError:
        return None


def token_is_valid(token: str) -> bool:
    """
    Returns True if the token decodes successfully without error.
    """
    try:
        decode_access_token(token)
        return True
    except JWTError:
        return False
