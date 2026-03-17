"""Authentication routes for KeyForge."""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timezone
from uuid import uuid4

try:
    from ..config import db
    from ..models import UserCreate, UserResponse
    from ..security import hash_password, verify_password, create_access_token, get_current_user
except ImportError:
    from backend.config import db
    from backend.models import UserCreate, UserResponse
    from backend.security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate):
    """Create a new user account."""
    # Check if username already exists
    existing_user = await db.users.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )

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


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and return a JWT access token."""
    user = await db.users.find_one({"username": form_data.username})
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    if not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get the currently authenticated user's information."""
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        created_at=current_user["created_at"],
    )
