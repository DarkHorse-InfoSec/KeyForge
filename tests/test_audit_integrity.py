"""Integration tests for audit chain integrity."""

import os
import pytest
from datetime import datetime, timezone

os.environ["ENCRYPTION_KEY"] = "Sx_Zd9AEzXhJz22Qzq5fSPb2KYXjnIJ2ZdIjk1aiQyY="
os.environ["JWT_SECRET"] = "test-jwt-secret-for-unit-tests"
os.environ["MONGO_URL"] = "mongodb://localhost:27017"
os.environ["DB_NAME"] = "keyforge_test"

from backend.audit.integrity import AuditIntegrity


@pytest.fixture
def sample_entry():
    return {
        "action": "credential.create",
        "user_id": "user-123",
        "timestamp": datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
        "details": {"credential_name": "my-api-key"},
    }


# ── compute_entry_hash ───────────────────────────────────────────────────


class TestComputeEntryHash:
    """AuditIntegrity.compute_entry_hash"""

    def test_is_deterministic(self, sample_entry):
        """Same inputs produce the same hash."""
        prev = AuditIntegrity.GENESIS_HASH
        h1 = AuditIntegrity.compute_entry_hash(sample_entry, prev)
        h2 = AuditIntegrity.compute_entry_hash(sample_entry, prev)
        assert h1 == h2

    def test_hash_is_64_char_hex(self, sample_entry):
        """Hash is a valid SHA-256 hex digest (64 characters)."""
        h = AuditIntegrity.compute_entry_hash(sample_entry, AuditIntegrity.GENESIS_HASH)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_changes_with_different_action(self, sample_entry):
        """Changing the action produces a different hash."""
        prev = AuditIntegrity.GENESIS_HASH
        h1 = AuditIntegrity.compute_entry_hash(sample_entry, prev)
        modified = {**sample_entry, "action": "credential.delete"}
        h2 = AuditIntegrity.compute_entry_hash(modified, prev)
        assert h1 != h2

    def test_changes_with_different_user(self, sample_entry):
        """Changing the user_id produces a different hash."""
        prev = AuditIntegrity.GENESIS_HASH
        h1 = AuditIntegrity.compute_entry_hash(sample_entry, prev)
        modified = {**sample_entry, "user_id": "user-999"}
        h2 = AuditIntegrity.compute_entry_hash(modified, prev)
        assert h1 != h2

    def test_includes_previous_hash_chaining(self, sample_entry):
        """Different previous_hash values produce different hashes (chain link)."""
        h1 = AuditIntegrity.compute_entry_hash(sample_entry, AuditIntegrity.GENESIS_HASH)
        h2 = AuditIntegrity.compute_entry_hash(sample_entry, "a" * 64)
        assert h1 != h2

    def test_changes_with_different_details(self, sample_entry):
        """Changing the details produces a different hash."""
        prev = AuditIntegrity.GENESIS_HASH
        h1 = AuditIntegrity.compute_entry_hash(sample_entry, prev)
        modified = {**sample_entry, "details": {"credential_name": "other-key"}}
        h2 = AuditIntegrity.compute_entry_hash(modified, prev)
        assert h1 != h2
