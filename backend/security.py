"""Security utilities: Fernet encryption for credentials, JWT auth, password hashing."""

import os
import warnings
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.config import db, logger

# ── Encryption (Fernet, for API keys at rest) ───────────────────────────────

_encryption_key = os.environ.get("ENCRYPTION_KEY")
if not _encryption_key:
    _encryption_key = Fernet.generate_key().decode()
    warnings.warn(
        "ENCRYPTION_KEY not set - generated a temporary key. "
        "Data encrypted in this session will NOT be recoverable after restart. "
        "Set the ENCRYPTION_KEY environment variable for persistence.",
        RuntimeWarning,
        stacklevel=1,
    )

_fernet = Fernet(_encryption_key if isinstance(_encryption_key, bytes) else _encryption_key.encode())


def encrypt_api_key(plain_key: str) -> str:
    """Encrypt a plaintext API key and return a base64 Fernet token string."""
    return _fernet.encrypt(plain_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt a Fernet token back to plaintext. Returns a placeholder on failure.

    Failures are logged WITHOUT the underlying exception text. The Fernet
    library can echo ciphertext fragments in its exceptions, and propagating
    those into the log is a leak risk. The audit trail records the fact of a
    failed decrypt; the specifics stay out of the logs.
    """
    try:
        return _fernet.decrypt(encrypted_key.encode()).decode()
    except (InvalidToken, Exception):
        logger.warning("Decryption failed (no further detail logged for security)")
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
    import secrets as _secrets

    JWT_SECRET = _secrets.token_urlsafe(64)
    warnings.warn(
        "JWT_SECRET not set - generated a random ephemeral secret. "
        "Tokens will NOT survive a restart. "
        "Set the JWT_SECRET environment variable for persistence.",
        RuntimeWarning,
        stacklevel=1,
    )

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a signed JWT containing *data* with an expiry claim."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
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


COOKIE_NAME = "keyforge_token"


def _extract_token(request: Request) -> str:
    """Return the JWT from the cookie (preferred) or Authorization header."""
    cookie_token = request.cookies.get(COOKIE_NAME)
    if cookie_token:
        return cookie_token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_token(request: Request) -> str:
    """FastAPI dependency: return the raw JWT string from cookie or header."""
    return _extract_token(request)


async def get_current_user(request: Request) -> dict:
    """Decode the JWT (from cookie or Authorization header) and load the user."""
    token = _extract_token(request)
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
