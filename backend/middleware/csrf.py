"""Double-submit cookie CSRF protection for browser-session requests."""

import logging
import os
import secrets

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("keyforge.csrf")

CSRF_COOKIE_NAME = "keyforge_csrf"
CSRF_HEADER_NAME = "x-csrf-token"
AUTH_COOKIE_NAME = "keyforge_token"

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
EXEMPT_PATHS = {"/api/auth/login", "/api/auth/register"}
MIN_TOKEN_LENGTH = 30


def _cookie_secure() -> bool:
    return os.environ.get("KEYFORGE_COOKIE_SECURE", "true").lower() != "false"


class CSRFMiddleware(BaseHTTPMiddleware):
    """Enforce double-submit CSRF on mutating /api/ requests from browser sessions."""

    async def dispatch(self, request: Request, call_next):
        method = request.method.upper()
        path = request.url.path
        is_api = path.startswith("/api/")
        is_mutating = method not in SAFE_METHODS
        is_exempt_path = path in EXEMPT_PATHS

        # Bearer-only requests (CLI/SDK) are not browser sessions and skip CSRF.
        auth_header = request.headers.get("Authorization", "")
        has_bearer = auth_header.lower().startswith("bearer ")
        has_auth_cookie = bool(request.cookies.get(AUTH_COOKIE_NAME))
        bearer_only = has_bearer and not has_auth_cookie

        if is_api and is_mutating and not is_exempt_path and not bearer_only:
            cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
            header_token = request.headers.get(CSRF_HEADER_NAME)
            if (
                not cookie_token
                or not header_token
                or len(cookie_token) < MIN_TOKEN_LENGTH
                or not secrets.compare_digest(cookie_token, header_token)
            ):
                logger.warning("CSRF token missing or invalid on %s %s", method, path)
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF token missing or invalid"},
                )

        response = await call_next(request)

        existing = request.cookies.get(CSRF_COOKIE_NAME)
        if not existing or len(existing) < MIN_TOKEN_LENGTH:
            response.set_cookie(
                key=CSRF_COOKIE_NAME,
                value=secrets.token_urlsafe(32),
                httponly=False,
                secure=_cookie_secure(),
                samesite="lax",
                path="/",
            )

        return response
