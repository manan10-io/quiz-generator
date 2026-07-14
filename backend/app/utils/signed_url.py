"""
signed_url.py — Stateless, tamper-proof, expiring download tokens.

Why not just a random UUID as the "download URL"? Because that would let
anyone who guesses/leaks a URL download the file forever, with no expiry
enforcement baked into the link itself. Instead we embed the record ID and
expiry timestamp directly in the token and sign it with HMAC-SHA256 using
the app's JWT secret, so:

  - The token is self-verifying: no DB lookup is needed to check expiry
    or detect tampering — only to confirm the record still exists.
  - A leaked/shared link stops working automatically once expires_at passes,
    with zero cleanup-job dependency for *security* (cleanup jobs still run
    to reclaim disk space, but expired links fail closed even if the sweep
    hasn't run yet).
  - Changing the record ID or expiry in the token invalidates the signature,
    so links can't be edited to extend their own lifetime.

Token format:  base64url(record_id:expiry_unix_ts) + "." + hex_hmac_signature
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
from datetime import datetime, timezone
from typing import Optional

from app.config import settings


def _sign(payload: str) -> str:
    return hmac.new(
        settings.JWT_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def generate_download_token(record_id: str, expires_at: datetime) -> str:
    """
    Build a signed token embedding the export record ID and its expiry.

    `expires_at` should be timezone-aware; naive datetimes are assumed UTC.
    """
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    expiry_ts = int(expires_at.timestamp())
    payload = f"{record_id}:{expiry_ts}"
    payload_b64 = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")
    signature = _sign(payload)

    return f"{payload_b64}.{signature}"


def verify_download_token(token: str) -> Optional[str]:
    """
    Verify a token's signature and expiry.

    Returns the record_id if the token is valid and not expired.
    Returns None if the token is malformed, tampered with, or expired.
    """
    if not token or "." not in token:
        return None

    payload_b64, _, signature = token.partition(".")
    if not payload_b64 or not signature:
        return None

    try:
        # Re-pad base64url before decoding (we stripped padding when encoding)
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = base64.urlsafe_b64decode(padded).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None

    # Recompute expected signature and compare using a constant-time check
    # to avoid leaking timing information about how much of the signature
    # matched (standard defence against timing side-channel attacks on
    # signature verification).
    expected_signature = _sign(payload)
    if not hmac.compare_digest(signature, expected_signature):
        return None

    record_id, _, expiry_str = payload.rpartition(":")
    if not record_id or not expiry_str:
        return None

    try:
        expiry_ts = int(expiry_str)
    except ValueError:
        return None

    if time.time() > expiry_ts:
        return None  # expired

    return record_id


def token_expiry(token: str) -> Optional[datetime]:
    """
    Extract the expiry datetime from a token WITHOUT verifying its signature.
    Useful for displaying "expires in X hours" to the user even for tokens
    that might otherwise fail strict verification (e.g. already expired).
    Do not use this for access-control decisions — use verify_download_token.
    """
    if not token or "." not in token:
        return None
    payload_b64, _, _ = token.partition(".")
    try:
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = base64.urlsafe_b64decode(padded).decode("utf-8")
        _, _, expiry_str = payload.rpartition(":")
        return datetime.fromtimestamp(int(expiry_str), tz=timezone.utc)
    except (ValueError, UnicodeDecodeError):
        return None
