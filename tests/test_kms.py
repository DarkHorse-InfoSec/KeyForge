"""Integration tests for KMS providers."""

import os
import pytest
from unittest.mock import patch

os.environ["ENCRYPTION_KEY"] = "Sx_Zd9AEzXhJz22Qzq5fSPb2KYXjnIJ2ZdIjk1aiQyY="
os.environ["JWT_SECRET"] = "test-jwt-secret-for-unit-tests"
os.environ["MONGO_URL"] = "mongodb://localhost:27017"
os.environ["DB_NAME"] = "keyforge_test"

from cryptography.fernet import Fernet
from backend.encryption.kms import (
    KMSProvider,
    LocalKMSProvider,
    get_kms_provider,
    _instance,
)


# ── LocalKMSProvider ─────────────────────────────────────────────────────


class TestLocalKMSProvider:
    """Tests for LocalKMSProvider."""

    def test_encrypt_decrypt_roundtrip(self):
        provider = LocalKMSProvider()
        plaintext = b"my-secret-data"
        ciphertext = provider.encrypt(plaintext)
        assert ciphertext != plaintext
        recovered = provider.decrypt(ciphertext)
        assert recovered == plaintext

    def test_generate_data_key(self):
        provider = LocalKMSProvider()
        plaintext_key, encrypted_key = provider.generate_data_key()
        assert isinstance(plaintext_key, bytes)
        assert isinstance(encrypted_key, bytes)
        # The plaintext key should be a valid Fernet key
        f = Fernet(plaintext_key)
        assert f is not None
        # Decrypting the encrypted_key should yield the plaintext_key
        recovered = provider.decrypt(encrypted_key)
        assert recovered == plaintext_key

    def test_get_status(self):
        provider = LocalKMSProvider()
        status = provider.get_status()
        assert status["provider"] == "local"
        assert "algorithm" in status
        assert "initialized_at" in status


# ── get_kms_provider factory ─────────────────────────────────────────────


class TestGetKMSProvider:
    """Tests for get_kms_provider factory function."""

    def test_returns_local_by_default(self):
        """When KMS_PROVIDER is unset or 'local', returns LocalKMSProvider."""
        import backend.encryption.kms as kms_module
        # Reset the cached instance
        kms_module._instance = None
        with patch.dict(os.environ, {"KMS_PROVIDER": "local"}, clear=False):
            provider = get_kms_provider()
            assert isinstance(provider, LocalKMSProvider)
        # Reset again for test isolation
        kms_module._instance = None

    def test_unknown_provider_raises(self):
        """Unknown KMS_PROVIDER value raises RuntimeError."""
        import backend.encryption.kms as kms_module
        kms_module._instance = None
        with patch.dict(os.environ, {"KMS_PROVIDER": "unknown_provider"}, clear=False):
            with pytest.raises(RuntimeError, match="Unknown KMS_PROVIDER"):
                get_kms_provider()
        kms_module._instance = None


# ── KMSProvider ABC ──────────────────────────────────────────────────────


class TestKMSProviderABC:
    """Tests for KMSProvider abstract base class."""

    def test_cannot_instantiate_abc(self):
        """KMSProvider is abstract and cannot be instantiated directly."""
        with pytest.raises(TypeError):
            KMSProvider()
