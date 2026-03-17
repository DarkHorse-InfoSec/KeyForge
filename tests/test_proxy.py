"""Integration tests for proxy token manager and provider injection."""

import os
import base64
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["ENCRYPTION_KEY"] = "Sx_Zd9AEzXhJz22Qzq5fSPb2KYXjnIJ2ZdIjk1aiQyY="
os.environ["JWT_SECRET"] = "test-jwt-secret-for-unit-tests"
os.environ["MONGO_URL"] = "mongodb://localhost:27017"
os.environ["DB_NAME"] = "keyforge_test"

from jose import jwt
from backend.proxy.credential_proxy import (
    ProxyTokenManager,
    PROVIDER_INJECTION_RULES,
    _inject_credential,
)
from backend.security import JWT_SECRET, JWT_ALGORITHM


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=MagicMock())
    proxy_coll = MagicMock()
    proxy_coll.insert_one = AsyncMock()
    proxy_coll.find_one = AsyncMock(return_value=None)
    db.__getitem__ = MagicMock(return_value=proxy_coll)
    return db


@pytest.fixture
def token_manager():
    return ProxyTokenManager()


# ── Proxy token creation ─────────────────────────────────────────────────


class TestProxyTokenCreation:
    """ProxyTokenManager.create_proxy_token"""

    @pytest.mark.asyncio
    async def test_create_returns_jwt(self, token_manager, mock_db):
        with patch("backend.proxy.credential_proxy.db", mock_db):
            result = await token_manager.create_proxy_token(
                user_id="user-1",
                credential_id="cred-1",
                ttl_seconds=300,
            )

        assert "proxy_token" in result
        assert "token_id" in result
        assert result["credential_id"] == "cred-1"
        assert result["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_token_is_valid_jwt(self, token_manager, mock_db):
        with patch("backend.proxy.credential_proxy.db", mock_db):
            result = await token_manager.create_proxy_token(
                user_id="user-1",
                credential_id="cred-1",
            )

        token = result["proxy_token"]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["sub"] == "user-1"
        assert payload["cid"] == "cred-1"
        assert payload["type"] == "proxy"
        assert "tid" in payload
        assert "exp" in payload

    @pytest.mark.asyncio
    async def test_allowed_endpoints_in_jwt(self, token_manager, mock_db):
        endpoints = ["https://api.openai.com/*"]
        with patch("backend.proxy.credential_proxy.db", mock_db):
            result = await token_manager.create_proxy_token(
                user_id="user-1",
                credential_id="cred-1",
                allowed_endpoints=endpoints,
            )

        payload = jwt.decode(result["proxy_token"], JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["eps"] == endpoints


# ── Provider injection patterns ──────────────────────────────────────────


class TestProviderInjection:
    """_inject_credential applies the correct injection pattern."""

    def test_bearer_injection(self):
        headers = {}
        params = {}
        _inject_credential("openai", "sk-test-key", headers, params)
        assert headers["Authorization"] == "Bearer sk-test-key"
        assert params == {}

    def test_basic_injection_username_is_key(self):
        """Stripe uses Basic auth with key as username."""
        headers = {}
        params = {}
        _inject_credential("stripe", "sk_live_xxx", headers, params)
        expected = base64.b64encode(b"sk_live_xxx:").decode()
        assert headers["Authorization"] == f"Basic {expected}"

    def test_basic_injection_password_is_key(self):
        """Twilio uses Basic auth with key as password."""
        headers = {}
        params = {}
        _inject_credential("twilio", "twilio-key", headers, params)
        expected = base64.b64encode(b":twilio-key").decode()
        assert headers["Authorization"] == f"Basic {expected}"

    def test_header_injection(self):
        """AWS uses X-API-Key header."""
        headers = {}
        params = {}
        _inject_credential("aws", "aws-key-123", headers, params)
        assert headers["X-API-Key"] == "aws-key-123"
        assert "Authorization" not in headers

    def test_query_injection(self):
        """Redis uses query parameter."""
        headers = {}
        params = {}
        _inject_credential("redis", "redis-key", headers, params)
        assert params["api_key"] == "redis-key"
        assert "Authorization" not in headers

    def test_unknown_provider_defaults_to_bearer(self):
        """Unknown providers fall back to Bearer auth."""
        headers = {}
        params = {}
        _inject_credential("unknown_provider", "some-key", headers, params)
        assert headers["Authorization"] == "Bearer some-key"
