"""
Input validation utilities for KeyForge.

Provides reusable validators for passwords, strings, URLs, and cron
expressions that can be used across routes and models.
"""

import re
import string
from urllib.parse import urlparse


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength.

    Requirements:
      - Minimum 8 characters
      - At least 1 uppercase letter
      - At least 1 lowercase letter
      - At least 1 digit
      - At least 1 special character

    Returns:
        (is_valid, message) - *message* describes the first failing rule,
        or "Password meets all requirements" on success.
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    # Special characters: anything that isn't alphanumeric or whitespace
    special_chars = set(string.punctuation)
    if not any(ch in special_chars for ch in password):
        return (
            False,
            "Password must contain at least one special character (!@#$%^&*...)",
        )
    return True, "Password meets all requirements"


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize a user-provided string.

    - Strips leading/trailing whitespace
    - Removes null bytes
    - Removes common control characters (U+0000–U+001F except tab/newline)
    - Truncates to *max_length*
    """
    # Remove null bytes
    value = value.replace("\x00", "")
    # Remove ASCII control characters except tab (0x09), newline (0x0A), carriage return (0x0D)
    value = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f]", "", value)
    # Strip whitespace
    value = value.strip()
    # Enforce length limit
    if len(value) > max_length:
        value = value[:max_length]
    return value


def validate_url(url: str) -> bool:
    """Validate that *url* is a well-formed HTTP(S) URL.

    Rejects non-HTTP schemes, URLs without a hostname, and private/internal
    addresses to mitigate SSRF risks.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    # Must be http or https
    if parsed.scheme not in ("http", "https"):
        return False

    # Must have a hostname
    hostname = parsed.hostname
    if not hostname:
        return False

    # Block obviously internal hostnames / IPs
    _blocked = (
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "169.254.169.254",  # AWS metadata
        "metadata.google.internal",  # GCP metadata
    )
    if hostname.lower() in _blocked:
        return False

    # Block private IP ranges (10.x, 172.16-31.x, 192.168.x)
    import ipaddress

    try:
        addr = ipaddress.ip_address(hostname)
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            return False
    except ValueError:
        pass  # Not an IP literal - that's fine

    return True


def validate_cron(expression: str) -> bool:
    """Validate a standard 5-field cron expression.

    Accepted format: ``minute hour day_of_month month day_of_week``

    Supports:
      - Integers within valid ranges
      - ``*`` (wildcard)
      - ``*/N`` (step values)
      - ``N-M`` (ranges)
      - ``N,M,...`` (lists)
    """
    parts = expression.strip().split()
    if len(parts) != 5:
        return False

    ranges = [
        (0, 59),  # minute
        (0, 23),  # hour
        (1, 31),  # day of month
        (1, 12),  # month
        (0, 7),  # day of week (0 and 7 both mean Sunday)
    ]

    for part, (lo, hi) in zip(parts, ranges):
        if not _validate_cron_field(part, lo, hi):
            return False
    return True


def _validate_cron_field(field: str, lo: int, hi: int) -> bool:
    """Validate a single cron field against its allowed range."""
    # Handle comma-separated lists
    for token in field.split(","):
        if not _validate_cron_token(token, lo, hi):
            return False
    return True


def _validate_cron_token(token: str, lo: int, hi: int) -> bool:
    """Validate one token (possibly with step or range) within a cron field."""
    # Step values: */N or N-M/S
    if "/" in token:
        base, _, step = token.partition("/")
        if not step.isdigit() or int(step) < 1:
            return False
        if base == "*":
            return True
        return _validate_cron_range(base, lo, hi)

    # Wildcard
    if token == "*":
        return True

    return _validate_cron_range(token, lo, hi)


def _validate_cron_range(token: str, lo: int, hi: int) -> bool:
    """Validate a plain integer or N-M range."""
    if "-" in token:
        parts = token.split("-", 1)
        if len(parts) != 2:
            return False
        if not (parts[0].isdigit() and parts[1].isdigit()):
            return False
        a, b = int(parts[0]), int(parts[1])
        return lo <= a <= hi and lo <= b <= hi and a <= b

    if not token.isdigit():
        return False
    val = int(token)
    return lo <= val <= hi
