"""Tests for per-user rate limiting in RateLimitMiddleware.

When the request carries a valid JWT (cookie or Authorization header), the
limiter should bucket by user identity instead of client IP. Anonymous
traffic continues to bucket by IP. A user who exhausts the limit on one path
must still be able to call other paths.
"""

# isort: skip_file
# Importing the shared test helpers MUST run before any backend module so
# that ENCRYPTION_KEY / JWT_SECRET are set to valid values; otherwise
# backend.security will raise at import time on a Fernet key check.
from tests._test_helpers import MOCK_DB  # noqa: F401  (import for side effects)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.middleware.rate_limiter import RateLimitMiddleware  # noqa: E402
from backend.security import create_access_token  # noqa: E402


def _build_app(requests_per_minute=2, burst_size=2):
    """Return a tiny FastAPI app wrapped in RateLimitMiddleware for isolated tests."""
    app = FastAPI()

    @app.get("/api/items")
    async def items():
        return {"ok": True}

    @app.get("/api/other")
    async def other():
        return {"ok": True}

    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=requests_per_minute,
        burst_size=burst_size,
        auth_requests_per_minute=requests_per_minute,
    )
    return app


def _drain_until_limited(client, path, headers=None, max_attempts=20):
    """Hit *path* until we get a 429, returning the count of successful 200s."""
    successes = 0
    for _ in range(max_attempts):
        resp = client.get(path, headers=headers or {})
        if resp.status_code == 429:
            return successes, resp
        if resp.status_code == 200:
            successes += 1
            continue
        raise AssertionError(f"unexpected status {resp.status_code}: {resp.text}")
    raise AssertionError("never hit rate limit")


class TestPerUserBucket:
    """Authenticated requests bucket by username, not by IP."""

    def test_same_user_different_ips_share_a_bucket(self):
        """Two valid tokens for the same user counted against one bucket."""
        app = _build_app(requests_per_minute=2, burst_size=2)
        token = create_access_token({"sub": "alice"})

        # Two distinct client IPs so we know the bucket key isn't IP-based.
        client_a = TestClient(app, base_url="http://1.1.1.1")
        client_b = TestClient(app, base_url="http://2.2.2.2")

        headers = {"Authorization": f"Bearer {token}"}

        # Burst is 2; we burn 1 from each client. Third request (from either)
        # should be 429 because both share the user:alice bucket for /api/items.
        r1 = client_a.get("/api/items", headers=headers)
        r2 = client_b.get("/api/items", headers=headers)
        r3 = client_a.get("/api/items", headers=headers)

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 429

    def test_token_in_cookie_is_recognised(self):
        """A valid JWT in the keyforge_token cookie should also bucket per user."""
        app = _build_app(requests_per_minute=2, burst_size=2)
        token = create_access_token({"sub": "bob"})

        client_a = TestClient(app, base_url="http://1.1.1.1")
        client_b = TestClient(app, base_url="http://2.2.2.2")
        client_a.cookies.set("keyforge_token", token)
        client_b.cookies.set("keyforge_token", token)

        r1 = client_a.get("/api/items")
        r2 = client_b.get("/api/items")
        r3 = client_b.get("/api/items")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 429


class TestAnonymousBucket:
    """Unauthenticated requests bucket by client IP as before."""

    def test_same_ip_anonymous_shares_bucket(self):
        """Two anonymous requests from the same IP count against one bucket."""
        app = _build_app(requests_per_minute=2, burst_size=2)

        client = TestClient(app, base_url="http://9.9.9.9")
        r1 = client.get("/api/items")
        r2 = client.get("/api/items")
        r3 = client.get("/api/items")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 429

    def test_invalid_token_falls_back_to_ip(self):
        """A bogus Authorization header is treated as anonymous."""
        app = _build_app(requests_per_minute=2, burst_size=2)

        # Same client IP for both, but two different garbage tokens. They
        # should still share the IP bucket because both decode to anonymous.
        client = TestClient(app, base_url="http://9.9.9.9")
        h1 = {"Authorization": "Bearer not.a.real.jwt"}
        h2 = {"Authorization": "Bearer also.bogus.token"}

        r1 = client.get("/api/items", headers=h1)
        r2 = client.get("/api/items", headers=h2)
        r3 = client.get("/api/items", headers=h1)

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 429


class TestCrossPathIsolation:
    """A bucket is keyed by (identity, path); other paths stay usable."""

    def test_user_limited_on_one_path_can_use_another(self):
        """Hitting the limit on /api/items must not block /api/other."""
        app = _build_app(requests_per_minute=2, burst_size=2)
        token = create_access_token({"sub": "carol"})
        headers = {"Authorization": f"Bearer {token}"}

        client = TestClient(app, base_url="http://3.3.3.3")
        # Drain /api/items.
        successes, limited = _drain_until_limited(client, "/api/items", headers=headers)
        assert successes == 2
        assert limited.status_code == 429

        # /api/other is a different bucket - first call still 200.
        resp_other = client.get("/api/other", headers=headers)
        assert resp_other.status_code == 200
