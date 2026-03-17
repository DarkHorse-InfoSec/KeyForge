"""Security utilities: Fernet encryption for credentials, JWT auth, password hashing."""

import os
import warnings
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.config import db, logger

# ── Encryption (Fernet, for API keys at rest) ───────────────────────────────

_encryption_key = os.environ.get("ENCRYPTION_KEY")
if not _encryption_key:
    _encryption_key = Fernet.generate_key().decode()
    warnings.warn(
        "ENCRYPTION_KEY not set — generated a temporary key. "
        "Data encrypted in this session will NOT be recoverable after restart. "
        "Set the ENCRYPTION_KEY environment variable for persistence.",
        RuntimeWarning,
        stacklevel=1,
    )

_fernet = Fernet(
    _encryption_key if isinstance(_encryption_key, bytes) else _encryption_key.encode()
)


def encrypt_api_key(plain_key: str) -> str:
    """Encrypt a plaintext API key and return a base64 Fernet token string."""
    return _fernet.encrypt(plain_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt a Fernet token back to plaintext. Returns a placeholder on failure."""
    try:
        return _fernet.decrypt(encrypted_key.encode()).decode()
    except (InvalidToken, Exception) as exc:
        logger.warning("Decryption failed: %s", exc)
        return "[decryption failed]"


# ── Password hashing (bcrypt) ───────────────────────────────────────────────

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Check *plain* against a bcrypt *hashed* value."""
    return _pwd_context.verify(plain, hashed)


# ── JWT authentication ──────────────────────────────────────────────────────

JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    JWT_SECRET = "insecure-dev-secret-change-me"
    warnings.warn(
        "JWT_SECRET not set — using an insecure default. "
        "Set the JWT_SECRET environment variable in production.",
        RuntimeWarning,
        stacklevel=1,
    )

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a signed JWT containing *data* with an expiry claim."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT. Raises HTTP 401 on any failure."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ── FastAPI dependency ──────────────────────────────────────────────────────

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Decode the bearer token, look up the user in MongoDB, and return it.

    Raises HTTP 401 if the token is invalid or the user no longer exists.
    """
    payload = decode_access_token(token)
    username: str | None = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await db.users.find_one({"username": username})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Convert ObjectId to string for JSON serialisability
    user["_id"] = str(user["_id"])
    return user
