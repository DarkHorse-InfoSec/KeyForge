"""
Global error handling middleware for consistent API responses.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("keyforge.errors")


class ErrorResponse:
    """Standardized error response format."""

    @staticmethod
    def create(status_code: int, message: str, details: Any = None, error_code: str = None) -> dict:
        response = {
            "error": True,
            "status_code": status_code,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if details:
            response["details"] = details
        if error_code:
            response["error_code"] = error_code
        return response


# Exception handlers to register with the FastAPI app
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTPException with standardized format."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse.create(
            status_code=exc.status_code,
            message=str(exc.detail),
        ),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with standardized format."""
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    return JSONResponse(
        status_code=422,
        content=ErrorResponse.create(
            status_code=422,
            message="Validation error",
            details=errors,
            error_code="VALIDATION_ERROR",
        ),
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions.

    Logs the exception type and traceback for debugging, but never
    exposes internal details in the response sent to the client.
    """
    # Log exception type and path; avoid interpolating raw user input.
    logger.error(
        "Unhandled %s on %s %s",
        type(exc).__name__,
        request.method,
        request.url.path,
        exc_info=True,  # Let the logging framework attach the traceback
    )
    return JSONResponse(
        status_code=500,
        content=ErrorResponse.create(
            status_code=500,
            message="Internal server error",
            error_code="INTERNAL_ERROR",
        ),
    )
