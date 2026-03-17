"""Integration tests for the envelope encryption module."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["ENCRYPTION_KEY"] = "Sx_Zd9AEzXhJz22Qzq5fSPb2KYXjnIJ2ZdIjk1aiQyY="
os.environ["JWT_SECRET"] = "test-jwt-secret-for-unit-tests"
os.environ["MONGO_URL"] = "mongodb://localhost:27017"
os.environ["DB_NAME"] = "keyforge_test"

from cryptography.fernet import Fernet
from backend.encryption.envelope import EnvelopeEncryption


@pytest.fixture
def master_key():
    """Return a stable Fernet key for testing."""
    return Fernet.generate_key().decode()


@pytest.fixture
def envelope(master_key):
    """Return an EnvelopeEncryption instance with a known master key."""
    return EnvelopeEncryption(master_key=master_key)


# ── generate_data_key ────────────────────────────────────────────────────


class TestGenerateDataKey:
    """EnvelopeEncryption.generate_data_key"""

    def test_returns_tuple_of_two(self, envelope):
        plaintext_key, encrypted_key = envelope.generate_data_key()
        assert isinstance(plaintext_key, bytes)
        assert isinstance(encrypted_key, str)

    def test_plaintext_key_is_valid_fernet_key(self, envelope):
        plaintext_key, _ = envelope.generate_data_key()
        # A valid Fernet key can be used to instantiate Fernet without error
        f = Fernet(plaintext_key)
        assert f is not None

    def test_encrypted_key_differs_from_plaintext(self, envelope):
        plaintext_key, encrypted_key = envelope.generate_data_key()
        assert encrypted_key != plaintext_key.decode()


# ── wrap / unwrap roundtrip ──────────────────────────────────────────────


class TestWrapUnwrap:
    """wrap_data_key / unwrap_data_key roundtrip."""

    def test_roundtrip(self, envelope):
        original_key = Fernet.generate_key()
        wrapped = envelope.wrap_data_key(original_key)
        unwrapped = envelope.unwrap_data_key(wrapped)
        assert unwrapped == original_key

    def test_wrapped_key_is_string(self, envelope):
        original_key = Fernet.generate_key()
        wrapped = envelope.wrap_data_key(original_key)
        assert isinstance(wrapped, str)


# ── encrypt / decrypt with data key ─────────────────────────────────────


class TestEncryptDecryptWithDataKey:
    """encrypt_with_data_key / decrypt_with_data_key roundtrip."""

    def test_roundtrip(self, envelope):
        data_key = Fernet.generate_key()
        plaintext = "super-secret-api-key-12345"
        ciphertext = envelope.encrypt_with_data_key(plaintext, data_key)
        recovered = envelope.decrypt_with_data_key(ciphertext, data_key)
        assert recovered == plaintext

    def test_ciphertext_differs_from_plaintext(self, envelope):
        data_key = Fernet.generate_key()
        plaintext = "my-api-key"
        ciphertext = envelope.encrypt_with_data_key(plaintext, data_key)
        assert ciphertext != plaintext


# ── encrypt_value / decrypt_value (async, high-level) ────────────────────


class TestEncryptDecryptValue:
    """encrypt_value / decrypt_value end-to-end envelope encryption."""

    @pytest.mark.asyncio
    async def test_encrypt_value_structure(self, envelope):
        """encrypt_value returns dict with ciphertext, wrapped_data_key, key_id."""
        mock_db = MagicMock()
        mock_db.user_data_keys = MagicMock()
        mock_db.user_data_keys.find_one = AsyncMock(return_value=None)
        mock_db.user_data_keys.insert_one = AsyncMock()

        with patch("backend.encryption.envelope.db", mock_db):
            result = await envelope.encrypt_value("hello-world", user_id="user-1")

        assert "ciphertext" in result
        assert "wrapped_data_key" in result
        assert "key_id" in result

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_value_roundtrip(self, envelope):
        """decrypt_value recovers the original plaintext."""
        mock_db = MagicMock()
        mock_db.user_data_keys = MagicMock()
        mock_db.user_data_keys.find_one = AsyncMock(return_value=None)
        mock_db.user_data_keys.insert_one = AsyncMock()

        with patch("backend.encryption.envelope.db", mock_db):
            plaintext = "my-super-secret-credential"
            encrypted = await envelope.encrypt_value(plaintext, user_id="user-1")
            decrypted = await envelope.decrypt_value(encrypted)
            assert decrypted == plaintext
