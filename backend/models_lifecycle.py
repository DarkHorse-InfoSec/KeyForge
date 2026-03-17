"""Pydantic models for credential lifecycle: expiration, permissions, versioning, auto-rotation."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

# ── Expiration models ─────────────────────────────────────────────────────────


class CredentialExpiration(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    credential_id: str
    user_id: str
    expires_at: datetime
    alert_days_before: int = 7  # Days before expiry to alert
    alert_sent: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CredentialExpirationCreate(BaseModel):
    credential_id: str
    expires_at: datetime
    alert_days_before: int = 7


class CredentialExpirationResponse(BaseModel):
    id: str
    credential_id: str
    api_name: str = ""
    expires_at: datetime
    days_until_expiry: int = 0
    alert_days_before: int
    is_expired: bool = False
    alert_sent: bool = False


# ── Permission models ─────────────────────────────────────────────────────────


class CredentialPermission(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    credential_id: str
    user_id: str  # The user being granted access
    granted_by: str  # The owner
    permission: str = "read"  # "read", "use", "manage", "admin"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CredentialPermissionCreate(BaseModel):
    credential_id: str
    username: str  # Look up user_id from username
    permission: str = "read"


class CredentialPermissionResponse(BaseModel):
    id: str
    credential_id: str
    api_name: str = ""
    user_id: str
    username: str = ""
    permission: str
    granted_by: str
    created_at: datetime


# ── Versioning models ─────────────────────────────────────────────────────────


class CredentialVersion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    credential_id: str
    user_id: str
    version_number: int
    api_key_encrypted: str
    change_reason: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_current: bool = True


class CredentialVersionResponse(BaseModel):
    id: str
    credential_id: str
    version_number: int
    api_key_preview: str  # Masked
    change_reason: str
    created_at: datetime
    is_current: bool


# ── Auto-rotation models ─────────────────────────────────────────────────────


class AutoRotationConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    credential_id: str
    user_id: str
    provider: str  # "aws", "github", "stripe"
    rotation_interval_days: int = 90
    last_rotated: Optional[datetime] = None
    next_rotation: Optional[datetime] = None
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AutoRotationConfigCreate(BaseModel):
    credential_id: str
    rotation_interval_days: int = 90
    enabled: bool = True
