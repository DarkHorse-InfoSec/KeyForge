"""Pydantic models for KeyForge security features: MFA, IP allowlisting, sessions, encryption."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
import uuid


# ── MFA models ────────────────────────────────────────────────────────────────

class MFASetup(BaseModel):
    """Response when enabling MFA — contains the TOTP secret and provisioning URI."""
    secret: str
    provisioning_uri: str
    backup_codes: List[str] = []


class MFAVerify(BaseModel):
    """Request body to verify a TOTP code."""
    code: str = Field(..., min_length=6, max_length=6)


class MFAStatusResponse(BaseModel):
    enabled: bool
    created_at: Optional[datetime] = None


# ── IP Allowlist models ───────────────────────────────────────────────────────

class IPAllowlistEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    ip_address: str  # Single IP or CIDR notation
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IPAllowlistCreate(BaseModel):
    ip_address: str = Field(..., min_length=7)  # Minimum valid IP
    description: str = ""


# ── Session models ────────────────────────────────────────────────────────────

class SessionInfo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    token_hash: str  # SHA-256 hash of the JWT
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True


class SessionResponse(BaseModel):
    id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    last_active: datetime
    is_current: bool = False


# ── Encryption admin models ──────────────────────────────────────────────────

class EncryptionKeyRotationRequest(BaseModel):
    new_key: Optional[str] = None  # If None, auto-generate


class EncryptionKeyRotationResponse(BaseModel):
    message: str
    credentials_re_encrypted: int
    timestamp: datetime
