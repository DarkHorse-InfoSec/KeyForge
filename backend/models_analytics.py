"""Pydantic models for KeyForge analytics, compliance, and lifecycle features."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, timezone
import uuid


# ── Breach detection models ──────────────────────────────────────────────────

class BreachCheckResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    credential_id: str
    user_id: str
    is_compromised: bool = False
    source: str = ""  # Which breach database checked
    check_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: str = ""


class BreachCheckResponse(BaseModel):
    credential_id: str
    api_name: str
    is_compromised: bool
    sources_checked: List[str]
    last_checked: datetime
    recommendation: str = ""


# ── Usage analytics models ───────────────────────────────────────────────────

class UsageEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    credential_id: str
    user_id: str
    action: str  # "tested", "viewed", "exported", "shared", "rotated"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UsageAnalytics(BaseModel):
    credential_id: str
    api_name: str
    total_uses: int = 0
    last_used: Optional[datetime] = None
    uses_last_7_days: int = 0
    uses_last_30_days: int = 0
    is_idle: bool = False  # No usage in 30+ days


# ── Compliance models ────────────────────────────────────────────────────────

class ComplianceReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    report_type: str  # "soc2", "gdpr", "general"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    summary: Dict = {}
    findings: List[Dict] = []


# ── Lifecycle models ─────────────────────────────────────────────────────────

class LifecycleEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    credential_id: str
    user_id: str
    event_type: str  # "created", "tested", "rotated", "shared", "expired", "revoked"
    details: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LifecycleTimelineResponse(BaseModel):
    credential_id: str
    api_name: str
    events: List[Dict] = []
    created_at: Optional[datetime] = None
    current_status: str = "unknown"
