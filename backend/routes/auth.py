"""Authentication routes for KeyForge."""

import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

try:
    from ..config import db
    from ..models import UserCreate, UserResponse
    from ..security import (
        ACCESS_TOKEN_EXPIRE_MINUTES,
        COOKIE_NAME,
        create_access_token,
        get_current_user,
        hash_password,
        verify_password,
    )
    from ..utils.validators import validate_password
except ImportError:
    from backend.config import db
    from backend.models import UserCreate, UserResponse
    from backend.security import (
        ACCESS_TOKEN_EXPIRE_MINUTES,
        COOKIE_NAME,
        create_access_token,
        get_current_user,
        hash_password,
        verify_password,
    )
    from backend.utils.validators import validate_password


class ChangePasswordRequest(BaseModel):
    """Body for POST /api/auth/change-password."""

    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


router = APIRouter(prefix="/api/auth", tags=["auth"])


def _cookie_secure() -> bool:
    """Return True unless KEYFORGE_COOKIE_SECURE is explicitly 'false' (for HTTP dev)."""
    return os.environ.get("KEYFORGE_COOKIE_SECURE", "true").lower() != "false"


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate):
    """Create a new user account."""
    # Enforce password complexity
    is_valid, msg = validate_password(user.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg)

    # Check if username already exists
    existing_user = await db.users.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Hash password and create user document
    hashed_pw = hash_password(user.password)
    user_doc = {
        "id": str(uuid4()),
        "username": user.username,
        "hashed_password": hashed_pw,
        "created_at": datetime.now(timezone.utc),
    }

    await db.users.insert_one(user_doc)

    return UserResponse(
        id=user_doc["id"],
        username=user_doc["username"],
        created_at=user_doc["created_at"],
    )


@router.post("/login", response_model=dict)
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user, set httpOnly cookie, and return a JWT access token in the body."""
    user = await db.users.find_one({"username": form_data.username})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token(data={"sub": user["username"]})
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path="/",
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }  # nosec B105  # reason: OAuth2 token-type label, not a credential


@router.post("/logout", response_model=dict)
async def logout(response: Response):
    """Clear the auth cookie. Body-token clients can simply discard their token."""
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"status": "ok"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get the currently authenticated user's information."""
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        created_at=current_user["created_at"],
    )


@router.post("/change-password", response_model=dict)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    """Change the authenticated user's password.

    Verifies the old password matches, runs the new password through the same
    complexity validator the registration endpoint uses, then writes the new
    bcrypt hash. Returns 400 on weak passwords or wrong old password (without
    leaking which one was wrong is unnecessary; the user already proved they
    own the session, so an explicit message is fine).
    """
    if not verify_password(payload.old_password, current_user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    is_valid, msg = validate_password(payload.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg)

    new_hash = hash_password(payload.new_password)
    await db.users.update_one(
        {"username": current_user["username"]},
        {"$set": {"hashed_password": new_hash}},
    )
    return {"status": "ok"}
