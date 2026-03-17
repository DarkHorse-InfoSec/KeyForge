"""Integration tests for expiration policy engine."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone

os.environ["ENCRYPTION_KEY"] = "Sx_Zd9AEzXhJz22Qzq5fSPb2KYXjnIJ2ZdIjk1aiQyY="
os.environ["JWT_SECRET"] = "test-jwt-secret-for-unit-tests"
os.environ["MONGO_URL"] = "mongodb://localhost:27017"
os.environ["DB_NAME"] = "keyforge_test"

from backend.policies.expiration_policy import ExpirationPolicy, DEFAULT_POLICY


def _make_policy_db(
    credential=None,
    exemption=None,
    rotation_req=None,
    expiration=None,
    policy=None,
):
    """Build a mock DB for expiration policy tests."""
    mock_db = MagicMock()

    mock_db.credentials = MagicMock()
    mock_db.credentials.find_one = AsyncMock(return_value=credential)

    mock_db.policy_exemptions = MagicMock()
    mock_db.policy_exemptions.find_one = AsyncMock(return_value=exemption)
    mock_db.policy_exemptions.delete_one = AsyncMock()

    mock_db.rotation_requirements = MagicMock()
    mock_db.rotation_requirements.find_one = AsyncMock(return_value=rotation_req)

    mock_db.expirations = MagicMock()
    mock_db.expirations.find_one = AsyncMock(return_value=expiration)

    mock_db.expiration_policies = MagicMock()
    mock_db.expiration_policies.find_one = AsyncMock(return_value=policy)

    return mock_db


_FAKE_CREDENTIAL = {
    "id": "cred-1",
    "user_id": "user-1",
    "api_name": "openai",
}


# ── Policy modes ─────────────────────────────────────────────────────────


class TestPolicyModes:
    """ExpirationPolicy.check_credential_access - mode behavior."""

    @pytest.mark.asyncio
    async def test_warn_mode_allows_expired(self):
        """In warn mode, expired credentials are still allowed."""
        expired_at = datetime.now(timezone.utc) - timedelta(days=3)
        policy_doc = {**DEFAULT_POLICY, "mode": "warn", "user_id": "user-1"}
        db = _make_policy_db(
            credential=_FAKE_CREDENTIAL,
            expiration={"credential_id": "cred-1", "user_id": "user-1", "expires_at": expired_at},
            policy=policy_doc,
        )
        result = await ExpirationPolicy.check_credential_access(db, "cred-1", "user-1")
        assert result["allowed"] is True
        assert result["policy_mode"] == "warn"

    @pytest.mark.asyncio
    async def test_block_mode_denies_expired(self):
        """In block mode, expired credentials are denied."""
        expired_at = datetime.now(timezone.utc) - timedelta(days=3)
        policy_doc = {**DEFAULT_POLICY, "mode": "block", "user_id": "user-1"}
        db = _make_policy_db(
            credential=_FAKE_CREDENTIAL,
            expiration={"credential_id": "cred-1", "user_id": "user-1", "expires_at": expired_at},
            policy=policy_doc,
        )
        result = await ExpirationPolicy.check_credential_access(db, "cred-1", "user-1")
        assert result["allowed"] is False
        assert result["policy_mode"] == "block"

    @pytest.mark.asyncio
    async def test_not_expired_always_allowed(self):
        """Non-expired credentials are always allowed regardless of mode."""
        future = datetime.now(timezone.utc) + timedelta(days=30)
        db = _make_policy_db(
            credential=_FAKE_CREDENTIAL,
            expiration={"credential_id": "cred-1", "user_id": "user-1", "expires_at": future},
        )
        result = await ExpirationPolicy.check_credential_access(db, "cred-1", "user-1")
        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def test_no_expiration_always_allowed(self):
        """Credentials without an expiration are always allowed."""
        db = _make_policy_db(credential=_FAKE_CREDENTIAL)
        result = await ExpirationPolicy.check_credential_access(db, "cred-1", "user-1")
        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def test_credential_not_found_denied(self):
        """Missing credential returns allowed=False."""
        db = _make_policy_db()
        result = await ExpirationPolicy.check_credential_access(db, "cred-99", "user-1")
        assert result["allowed"] is False


# ── Grace period ─────────────────────────────────────────────────────────


class TestGracePeriod:
    """Grace period calculation in grace mode."""

    @pytest.mark.asyncio
    async def test_within_grace_period_allowed(self):
        """Credential expired within grace period is allowed."""
        expired_at = datetime.now(timezone.utc) - timedelta(days=3)
        policy_doc = {**DEFAULT_POLICY, "mode": "grace", "grace_period_days": 7, "user_id": "user-1"}
        db = _make_policy_db(
            credential=_FAKE_CREDENTIAL,
            expiration={"credential_id": "cred-1", "user_id": "user-1", "expires_at": expired_at},
            policy=policy_doc,
        )
        result = await ExpirationPolicy.check_credential_access(db, "cred-1", "user-1")
        assert result["allowed"] is True
        assert result["policy_mode"] == "grace"
        assert result["grace_period_remaining"] > 0

    @pytest.mark.asyncio
    async def test_grace_period_exceeded_blocked(self):
        """Credential expired beyond grace period is blocked."""
        expired_at = datetime.now(timezone.utc) - timedelta(days=10)
        policy_doc = {**DEFAULT_POLICY, "mode": "grace", "grace_period_days": 7, "user_id": "user-1"}
        db = _make_policy_db(
            credential=_FAKE_CREDENTIAL,
            expiration={"credential_id": "cred-1", "user_id": "user-1", "expires_at": expired_at},
            policy=policy_doc,
        )
        result = await ExpirationPolicy.check_credential_access(db, "cred-1", "user-1")
        assert result["allowed"] is False
        assert result["policy_mode"] == "grace"
        assert result["grace_period_remaining"] == 0


# ── Exemption logic ──────────────────────────────────────────────────────


class TestExemption:
    """Exemption overrides policy enforcement."""

    @pytest.mark.asyncio
    async def test_exempt_credential_allowed_even_if_blocked(self):
        """An exempt credential is allowed even under block mode."""
        expired_at = datetime.now(timezone.utc) - timedelta(days=5)
        policy_doc = {**DEFAULT_POLICY, "mode": "block", "user_id": "user-1"}
        exemption_doc = {
            "id": "ex-1",
            "credential_id": "cred-1",
            "user_id": "user-1",
            "reason": "Legacy key",
        }
        db = _make_policy_db(
            credential=_FAKE_CREDENTIAL,
            exemption=exemption_doc,
            expiration={"credential_id": "cred-1", "user_id": "user-1", "expires_at": expired_at},
            policy=policy_doc,
        )
        result = await ExpirationPolicy.check_credential_access(db, "cred-1", "user-1")
        assert result["allowed"] is True
        assert result["policy_mode"] == "exempt"

    @pytest.mark.asyncio
    async def test_expired_exemption_not_honoured(self):
        """An exemption that has itself expired is ignored."""
        expired_at = datetime.now(timezone.utc) - timedelta(days=5)
        policy_doc = {**DEFAULT_POLICY, "mode": "block", "user_id": "user-1"}
        exemption_doc = {
            "id": "ex-1",
            "credential_id": "cred-1",
            "user_id": "user-1",
            "reason": "Temp exemption",
            "expires_at": datetime.now(timezone.utc) - timedelta(days=1),
        }
        db = _make_policy_db(
            credential=_FAKE_CREDENTIAL,
            exemption=exemption_doc,
            expiration={"credential_id": "cred-1", "user_id": "user-1", "expires_at": expired_at},
            policy=policy_doc,
        )
        result = await ExpirationPolicy.check_credential_access(db, "cred-1", "user-1")
        assert result["allowed"] is False
        assert result["policy_mode"] == "block"
