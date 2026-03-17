import pytest
import os

# Set test environment variables before importing backend modules
os.environ.setdefault("ENCRYPTION_KEY", "dGVzdGtleWZvcmtleWZvcmdlMTIzNDU2Nzg5MDEyMzQ1Ng==")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-keyforge-tests")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "keyforge_test")


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Reset rate limiter state before each test to prevent 429 errors."""
    try:
        from tests._test_helpers import reset_rate_limiter
        reset_rate_limiter()
    except Exception:
        pass
    yield
