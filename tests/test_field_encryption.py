"""Integration tests for field-level encryption."""

import os
import pytest

os.environ["ENCRYPTION_KEY"] = "Sx_Zd9AEzXhJz22Qzq5fSPb2KYXjnIJ2ZdIjk1aiQyY="
os.environ["JWT_SECRET"] = "test-jwt-secret-for-unit-tests"
os.environ["MONGO_URL"] = "mongodb://localhost:27017"
os.environ["DB_NAME"] = "keyforge_test"

from backend.encryption.field_encryption import FieldEncryptor, SENSITIVE_FIELDS


@pytest.fixture
def encryptor():
    return FieldEncryptor()


# ── encrypt_field / decrypt_field ────────────────────────────────────────


class TestFieldEncryptDecrypt:
    """FieldEncryptor.encrypt_field / decrypt_field roundtrip."""

    def test_roundtrip(self, encryptor):
        plaintext = "user@example.com"
        encrypted = encryptor.encrypt_field(plaintext)
        assert encrypted != plaintext
        decrypted = encryptor.decrypt_field(encrypted)
        assert decrypted == plaintext

    def test_ciphertext_is_string(self, encryptor):
        encrypted = encryptor.encrypt_field("test-value")
        assert isinstance(encrypted, str)

    def test_different_plaintexts_produce_different_ciphertexts(self, encryptor):
        c1 = encryptor.encrypt_field("value-a")
        c2 = encryptor.encrypt_field("value-b")
        assert c1 != c2


# ── encrypt_document with dot-notation ───────────────────────────────────


class TestDocumentEncryption:
    """FieldEncryptor.encrypt_document / decrypt_document."""

    def test_encrypt_document_top_level(self, encryptor):
        doc = {"email": "alice@example.com", "name": "Alice"}
        encrypted_doc = encryptor.encrypt_document(doc, ["email"])
        # email should be encrypted
        assert encrypted_doc["email"] != "alice@example.com"
        # name should be untouched
        assert encrypted_doc["name"] == "Alice"
        # Original doc should be unchanged (deep copy)
        assert doc["email"] == "alice@example.com"

    def test_encrypt_document_nested_dot_notation(self, encryptor):
        doc = {
            "details": {
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0",
            },
            "action": "login",
        }
        fields = ["details.ip_address", "details.user_agent"]
        encrypted_doc = encryptor.encrypt_document(doc, fields)
        assert encrypted_doc["details"]["ip_address"] != "192.168.1.1"
        assert encrypted_doc["details"]["user_agent"] != "Mozilla/5.0"
        assert encrypted_doc["action"] == "login"

    def test_encrypt_decrypt_document_roundtrip(self, encryptor):
        doc = {
            "details": {"ip_address": "10.0.0.1"},
            "user_id": "user-1",
        }
        fields = ["details.ip_address"]
        encrypted_doc = encryptor.encrypt_document(doc, fields)
        decrypted_doc = encryptor.decrypt_document(encrypted_doc, fields)
        assert decrypted_doc["details"]["ip_address"] == "10.0.0.1"
        assert decrypted_doc["user_id"] == "user-1"

    def test_missing_field_silently_skipped(self, encryptor):
        doc = {"name": "Bob"}
        # Encrypting a non-existent field should not raise
        encrypted_doc = encryptor.encrypt_document(doc, ["email"])
        assert encrypted_doc == {"name": "Bob"}


# ── encrypt_search_hash ──────────────────────────────────────────────────


class TestSearchHash:
    """FieldEncryptor.encrypt_search_hash."""

    def test_is_deterministic(self, encryptor):
        h1 = encryptor.encrypt_search_hash("alice@example.com")
        h2 = encryptor.encrypt_search_hash("alice@example.com")
        assert h1 == h2

    def test_different_values_produce_different_hashes(self, encryptor):
        h1 = encryptor.encrypt_search_hash("alice@example.com")
        h2 = encryptor.encrypt_search_hash("bob@example.com")
        assert h1 != h2

    def test_hash_is_hex_string(self, encryptor):
        h = encryptor.encrypt_search_hash("test")
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex digest
        assert all(c in "0123456789abcdef" for c in h)


# ── SENSITIVE_FIELDS config ──────────────────────────────────────────────


class TestSensitiveFieldsConfig:
    """SENSITIVE_FIELDS has expected collections."""

    def test_expected_collections_present(self):
        expected = {"users", "audit_log", "teams", "webhooks", "sessions"}
        assert expected.issubset(set(SENSITIVE_FIELDS.keys()))

    def test_users_has_email(self):
        assert "email" in SENSITIVE_FIELDS["users"]

    def test_audit_log_has_ip_and_user_agent(self):
        assert "details.ip_address" in SENSITIVE_FIELDS["audit_log"]
        assert "details.user_agent" in SENSITIVE_FIELDS["audit_log"]
