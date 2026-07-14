"""
auth.py — FastAPI router for /auth/* endpoints.

Routes:
  POST /auth/google        — Receive Google credentials from NextAuth, issue JWT
  GET  /auth/me            — Return current user profile (requires JWT)
  DELETE /auth/logout      — Client-side logout (JWT is stateless; just 200 OK)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.models import User
from app.schemas.schemas import (
    AuthResponse, GoogleAuthRequest, UserOut, UserSettings, UserSettingsUpdate,
)
from app.services.auth_service import auth_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── POST /auth/google ────────────────────────────────────────────────────────

@router.post("/google", response_model=AuthResponse)
async def google_signin(
    payload: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Called by Next.js/NextAuth after the Google OAuth browser flow completes.
    Upserts the user record and issues a JWT for subsequent API calls.
    """
    try:
        response = await auth_service.google_signin(payload, db)
        return response
    except Exception as e:
        logger.error("Google sign-in failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )


# ─── GET /auth/me ─────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile and settings."""
    return UserOut(
        id=current_user.id,
        google_id=current_user.google_id,
        email=current_user.email,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        settings=UserSettings(**(current_user.settings or {})),
        created_at=current_user.created_at,
    )


# ─── DELETE /auth/logout ──────────────────────────────────────────────────────

@router.delete("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: User = Depends(get_current_user)):
    """
    JWT is stateless — there's nothing to invalidate server-side.
    The client simply discards the token. This endpoint exists so the frontend
    can make a clean HTTP call on sign-out (useful for future token revocation).
    """
    return None


# ─── GET /auth/google/callback (redirect endpoint for direct OAuth flow) ──────

@router.get("/google/callback")
async def google_callback():
    """
    Placeholder for the direct OAuth redirect flow (not used when NextAuth
    handles the frontend OAuth). Returns 200 to confirm the route exists.
    """
    return {"message": "Use the NextAuth callback route on the frontend."}
