"""
Token bucket rate limiter for FastAPI.

Buckets requests by authenticated user when a valid JWT is present (cookie or
Authorization header), and falls back to per-IP buckets for anonymous traffic.
A user hitting the limit on one path can still use other paths because the
bucket key includes the request path.
"""

import logging
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.security import COOKIE_NAME, JWT_ALGORITHM, JWT_SECRET

logger = logging.getLogger("keyforge.rate_limiter")


def _extract_identity(request: Request) -> str:
    """
    Return a stable bucket identity for the request.

    Prefers an authenticated user (``user:<username>``) when a valid JWT is
    found in either the auth cookie or the ``Authorization: Bearer ...``
    header. Falls back to ``ip:<client_ip>`` for anonymous or
    invalid-token requests.

    Decoding failures are treated as anonymous; we do not raise here because
    this middleware runs before route auth dependencies and must not pre-empt
    their error handling.
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            username = payload.get("sub")
            if username:
                return f"user:{username}"
        except JWTError:
            pass  # fall through to IP-based bucket

    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using token bucket algorithm.

    Args:
        app: FastAPI application
        requests_per_minute: Max requests per minute per identity (default 60)
        burst_size: Max burst size (default 10)
        auth_requests_per_minute: Stricter limit for auth endpoints (default 10)
    """

    def __init__(self, app, requests_per_minute=60, burst_size=10, auth_requests_per_minute=10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.auth_requests_per_minute = auth_requests_per_minute
        self._buckets = defaultdict(lambda: {"tokens": burst_size, "last_refill": time.time()})
        self._auth_buckets = defaultdict(lambda: {"tokens": 5, "last_refill": time.time()})

    async def dispatch(self, request: Request, call_next):
        identity = _extract_identity(request)
        path = request.url.path

        # Stricter limits for auth endpoints
        is_auth = path.startswith("/api/auth/login") or path.startswith("/api/auth/register")

        bucket_key = (identity, path)
        if is_auth:
            bucket = self._auth_buckets[bucket_key]
            rate = self.auth_requests_per_minute
        else:
            bucket = self._buckets[bucket_key]
            rate = self.requests_per_minute

        # Refill tokens
        now = time.time()
        elapsed = now - bucket["last_refill"]
        refill = elapsed * (rate / 60.0)
        max_tokens = self.burst_size if not is_auth else 5
        bucket["tokens"] = min(max_tokens, bucket["tokens"] + refill)
        bucket["last_refill"] = now

        # Check if request is allowed
        if bucket["tokens"] < 1:
            logger.warning("Rate limit exceeded for %s on %s", identity, path)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after_seconds": int(60 / rate),
                },
                headers={"Retry-After": str(int(60 / rate))},
            )

        bucket["tokens"] -= 1
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(rate)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket["tokens"]))

        return response


class RateLimiter:
    """
    Dependency-based rate limiter for granular control on specific routes.

    Usage:
        @router.post("/sensitive-endpoint")
        async def endpoint(request: Request, _=Depends(RateLimiter(max_requests=5, window_seconds=60))):
            ...
    """

    _store = defaultdict(list)

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def __call__(self, request: Request):
        identity = _extract_identity(request)
        key = f"{identity}:{request.url.path}"
        now = time.time()

        # Clean old entries
        RateLimiter._store[key] = [t for t in RateLimiter._store[key] if now - t < self.window_seconds]

        if len(RateLimiter._store[key]) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds}s.",
            )

        RateLimiter._store[key].append(now)
