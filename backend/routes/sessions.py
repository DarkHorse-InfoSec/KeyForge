"""Session management routes for KeyForge."""

import hashlib
import hmac
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional

from backend.config import db, logger
from backend.security import get_current_user, oauth2_scheme
from backend.models_security import SessionInfo, SessionResponse

router = APIRouter(prefix="/api", tags=["sessions"])


def _hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of *token*."""
    return hashlib.sha256(token.encode()).hexdigest()


class RecordSessionRequest(BaseModel):
    token: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    request: Request,
    current_user: dict = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
):
    """List all active sessions for the current user.

    The session matching the current bearer token is marked with ``is_current: true``.
    """
    current_token_hash = _hash_token(token)

    sessions = await db.sessions.find(
        {"user_id": current_user["id"], "is_active": True}
    ).to_list(length=500)

    results = []
    for sess in sessions:
        results.append(
            SessionResponse(
                id=sess["id"],
                ip_address=sess.get("ip_address"),
                user_agent=sess.get("user_agent"),
                created_at=sess["created_at"],
                last_active=sess["last_active"],
                is_current=hmac.compare_digest(sess["token_hash"], current_token_hash),
            )
        )

    return results


@router.delete("/sessions/{session_id}", response_model=dict)
async def revoke_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
):
    """Revoke (deactivate) a specific session. Cannot revoke the current session."""
    current_token_hash = _hash_token(token)

    session = await db.sessions.find_one(
        {"id": session_id, "user_id": current_user["id"], "is_active": True}
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if hmac.compare_digest(session["token_hash"], current_token_hash):
        raise HTTPException(status_code=400, detail="Cannot revoke the current session")

    await db.sessions.update_one(
        {"id": session_id},
        {"$set": {"is_active": False}},
    )

    logger.info(
        "Session %s revoked for user %s", session_id, current_user["username"]
    )
    return {"message": "Session revoked"}


@router.delete("/sessions", response_model=dict)
async def revoke_all_sessions(
    current_user: dict = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
):
    """Revoke all active sessions except the current one (logout everywhere else)."""
    current_token_hash = _hash_token(token)

    result = await db.sessions.update_many(
        {
            "user_id": current_user["id"],
            "is_active": True,
            "token_hash": {"$ne": current_token_hash},
        },
        {"$set": {"is_active": False}},
    )

    logger.info(
        "Revoked %d other sessions for user %s",
        result.modified_count,
        current_user["username"],
    )
    return {"message": f"Revoked {result.modified_count} sessions"}


@router.post("/sessions/record", response_model=dict)
async def record_session(
    body: RecordSessionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Internal helper — record a new session after login.

    Stores a SHA-256 hash of the JWT (never the raw token).
    """
    session = SessionInfo(
        user_id=current_user["id"],
        token_hash=_hash_token(body.token),
        ip_address=body.ip_address,
        user_agent=body.user_agent,
    )

    await db.sessions.insert_one(session.model_dump())

    logger.info(
        "Session recorded for user %s from %s",
        current_user["username"],
        body.ip_address,
    )
    return {"message": "Session recorded", "session_id": session.id}
