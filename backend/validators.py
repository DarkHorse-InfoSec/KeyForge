"""
Real credential validators for supported API providers.
Validates key format and optionally tests against the real API.
"""
import re
import logging
import time
import requests
from typing import Dict

logger = logging.getLogger("keyforge.validators")


def _validate_format_openai(api_key: str) -> str | None:
    """Validate OpenAI key format. Returns error message or None if valid."""
    if not api_key.startswith("sk-"):
        return "OpenAI keys must start with 'sk-'"
    if len(api_key) < 40:
        return "OpenAI keys must be at least 40 characters"
    return None


def _validate_format_stripe(api_key: str) -> str | None:
    """Validate Stripe key format. Returns error message or None if valid."""
    valid_prefixes = ("sk_test_", "sk_live_", "pk_test_", "pk_live_")
    if not any(api_key.startswith(p) for p in valid_prefixes):
        return "Stripe keys must start with 'sk_test_', 'sk_live_', 'pk_test_', or 'pk_live_'"
    if len(api_key) < 20:
        return "Stripe keys must be at least 20 characters"
    return None


def _validate_format_github(api_key: str) -> str | None:
    """Validate GitHub key format. Returns error message or None if valid."""
    valid_prefixes = ("ghp_", "gho_", "ghs_", "github_pat_", "gh")
    if not any(api_key.startswith(p) for p in valid_prefixes):
        return "GitHub keys must start with 'ghp_', 'gho_', 'ghs_', 'github_pat_', or 'gh' prefix"
    if len(api_key) < 20:
        return "GitHub keys must be at least 20 characters"
    return None


def _validate_format_supabase(api_key: str) -> str | None:
    """Validate Supabase key format. Returns error message or None if valid."""
    # Check JWT-like format: three dot-separated base64 segments
    parts = api_key.split(".")
    if len(parts) == 3:
        base64_pattern = re.compile(r'^[A-Za-z0-9_-]+$')
        if all(base64_pattern.match(part) for part in parts if part):
            return None
    # Also accept long alphanumeric strings
    if re.match(r'^[A-Za-z0-9]{20,}$', api_key):
        return None
    return "Supabase keys must be a valid JWT (3 dot-separated base64 segments) or a long alphanumeric string"


def _validate_format_firebase(api_key: str) -> str | None:
    """Validate Firebase key format. Returns error message or None if valid."""
    if len(api_key) < 30:
        return "Firebase keys must be at least 30 characters"
    if not re.match(r'^[A-Za-z0-9_-]+$', api_key):
        return "Firebase keys must be alphanumeric"
    return None


def _validate_format_vercel(api_key: str) -> str | None:
    """Validate Vercel key format. Returns error message or None if valid."""
    if len(api_key) < 20:
        return "Vercel keys must be at least 20 characters"
    return None


FORMAT_VALIDATORS = {
    "openai": _validate_format_openai,
    "stripe": _validate_format_stripe,
    "github": _validate_format_github,
    "supabase": _validate_format_supabase,
    "firebase": _validate_format_firebase,
    "vercel": _validate_format_vercel,
}

# Providers that support live API validation
LIVE_VALIDATION_PROVIDERS = {"openai", "stripe", "github"}


def _live_validate_openai(api_key: str) -> Dict:
    """Validate an OpenAI key against the real API."""
    response = requests.get(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=10,
    )
    elapsed_ms = int(response.elapsed.total_seconds() * 1000)

    if response.status_code == 200:
        return {"status": "active", "response_time": elapsed_ms, "message": "Credential validated successfully"}
    elif response.status_code == 401:
        return {"status": "invalid", "response_time": elapsed_ms, "message": "Invalid API key (unauthorized)"}
    elif response.status_code == 429:
        return {"status": "rate_limited", "response_time": elapsed_ms, "message": "Rate limit exceeded"}
    else:
        return {
            "status": "format_valid",
            "response_time": elapsed_ms,
            "message": f"Key format is valid but API returned status {response.status_code}",
        }


def _live_validate_stripe(api_key: str) -> Dict:
    """Validate a Stripe key against the real API."""
    response = requests.get(
        "https://api.stripe.com/v1/balance",
        auth=(api_key, ""),
        timeout=10,
    )
    elapsed_ms = int(response.elapsed.total_seconds() * 1000)

    if response.status_code == 200:
        return {"status": "active", "response_time": elapsed_ms, "message": "Credential validated successfully"}
    elif response.status_code == 401:
        return {"status": "invalid", "response_time": elapsed_ms, "message": "Invalid API key (unauthorized)"}
    elif response.status_code == 429:
        return {"status": "rate_limited", "response_time": elapsed_ms, "message": "Rate limit exceeded"}
    else:
        return {
            "status": "format_valid",
            "response_time": elapsed_ms,
            "message": f"Key format is valid but API returned status {response.status_code}",
        }


def _live_validate_github(api_key: str) -> Dict:
    """Validate a GitHub token against the real API."""
    response = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=10,
    )
    elapsed_ms = int(response.elapsed.total_seconds() * 1000)

    if response.status_code == 200:
        return {"status": "active", "response_time": elapsed_ms, "message": "Credential validated successfully"}
    elif response.status_code == 401:
        return {"status": "invalid", "response_time": elapsed_ms, "message": "Invalid API key (unauthorized)"}
    elif response.status_code == 403:
        return {"status": "expired", "response_time": elapsed_ms, "message": "Token expired or rate limited"}
    else:
        return {
            "status": "format_valid",
            "response_time": elapsed_ms,
            "message": f"Key format is valid but API returned status {response.status_code}",
        }


LIVE_VALIDATORS = {
    "openai": _live_validate_openai,
    "stripe": _live_validate_stripe,
    "github": _live_validate_github,
}


def validate_credential(api_name: str, api_key: str) -> Dict:
    """
    Validate a credential with format checking and optional live API validation.

    Returns:
        Dict with keys: status, response_time, message
        status is one of: active, invalid, expired, rate_limited, format_valid, timeout
    """
    provider = api_name.lower()

    # Step 1: Format validation
    format_validator = FORMAT_VALIDATORS.get(provider)
    if format_validator is None:
        # Unknown provider — can only do a basic length check
        if len(api_key) < 8:
            return {"status": "invalid", "response_time": 0, "message": "Invalid key format: key is too short"}
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": f"No specific validator for '{api_name}'. Key length looks acceptable.",
        }

    format_error = format_validator(api_key)
    if format_error is not None:
        return {"status": "invalid", "response_time": 0, "message": f"Invalid key format: {format_error}"}

    # Step 2: Live API validation (only for providers that support it)
    live_validator = LIVE_VALIDATORS.get(provider)
    if live_validator is None:
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": "Key format is valid. Live validation requires project configuration.",
        }

    try:
        return live_validator(api_key)
    except requests.Timeout:
        logger.warning("Timeout validating %s credential", api_name)
        return {"status": "timeout", "response_time": 10000, "message": "API request timed out"}
    except requests.ConnectionError:
        logger.warning("Connection error validating %s credential", api_name)
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": "Format valid but could not reach API",
        }
    except Exception:
        logger.exception("Unexpected error validating %s credential", api_name)
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": "Format valid but live validation encountered an error",
        }
