"""GPG and code-signing key detection patterns and validators for KeyForge."""

import logging
import re
from typing import Dict

logger = logging.getLogger("keyforge.signing_keys")

# Signing Key Detection Patterns (matches API_PATTERNS format)
PATTERNS = {
    "gpg": {
        "name": "GPG",
        "category": "Signing",
        "patterns": [
            r"BEGIN PGP PRIVATE KEY",
            r"BEGIN PGP PUBLIC KEY",
            r"GPG_PRIVATE_KEY",
            r"GPG_KEY",
            r"gpg --import",
            r"SIGNING_KEY",
        ],
        "files": [".py", ".sh", ".yml", ".yaml", ".env", ".conf"],
        "auth_type": "private_key",
        "scopes": ["commit_signing", "package_signing", "encryption", "verification"],
    },
    "jwt_signing": {
        "name": "JWT Signing",
        "category": "Signing",
        "patterns": [
            r"JWT_SECRET",
            r"JWT_SIGNING_KEY",
            r"JWT_PRIVATE_KEY",
            r"RS256",
            r"ES256",
            r"BEGIN RSA PRIVATE KEY.*jwt",
            r"jsonwebtoken",
        ],
        "files": [".py", ".js", ".ts", ".env", ".yml", ".yaml"],
        "auth_type": "secret",
        "scopes": ["token_signing", "token_verification"],
    },
}

# Valid PGP block types
_VALID_PGP_TYPES = (
    "PGP PRIVATE KEY BLOCK",
    "PGP PUBLIC KEY BLOCK",
    "PGP PRIVATE KEY",
    "PGP PUBLIC KEY",
)


def validate_gpg_key(key: str) -> Dict:
    """
    Validate a GPG/PGP key by checking its PGP header format.

    Verifies BEGIN/END armor markers and that the body is non-empty.
    No live validation is performed.

    Returns:
        Dict with keys: status, response_time, message
    """
    key = key.strip()

    if not key.startswith("-----BEGIN"):
        return {
            "status": "invalid",
            "response_time": 0,
            "message": "GPG key must start with a '-----BEGIN PGP ...' armor header",
        }

    begin_match = re.match(r"^-----BEGIN (.+?)-----", key)
    if begin_match is None:
        return {
            "status": "invalid",
            "response_time": 0,
            "message": "Malformed PGP header: could not parse BEGIN marker",
        }

    pgp_type = begin_match.group(1)

    if pgp_type not in _VALID_PGP_TYPES:
        return {
            "status": "invalid",
            "response_time": 0,
            "message": f"Unrecognized PGP block type: '{pgp_type}'. " f"Expected one of: {', '.join(_VALID_PGP_TYPES)}",
        }

    expected_end = f"-----END {pgp_type}-----"
    if expected_end not in key:
        return {
            "status": "invalid",
            "response_time": 0,
            "message": f"PGP armor invalid: missing '{expected_end}' marker",
        }

    # Check that the body between markers is non-empty
    body_match = re.search(
        rf"-----BEGIN {re.escape(pgp_type)}-----\s*(.+?)\s*-----END {re.escape(pgp_type)}-----",
        key,
        re.DOTALL,
    )
    if body_match is None or not body_match.group(1).strip():
        return {
            "status": "invalid",
            "response_time": 0,
            "message": "PGP key body is empty",
        }

    key_kind = "private" if "PRIVATE" in pgp_type else "public"
    return {
        "status": "format_valid",
        "response_time": 0,
        "message": f"Detected valid PGP-armored {key_kind} key ({pgp_type})",
    }


# PEM types accepted as JWT signing keys
_JWT_PEM_TYPES = ("RSA PRIVATE KEY", "EC PRIVATE KEY")


def validate_jwt_signing_key(key: str) -> Dict:
    """
    Validate a JWT signing key.

    Accepts either:
      - A PEM-formatted RSA or EC private key (for RS256, ES256, etc.)
      - A plain secret string of at least 32 characters (for HS256, etc.)

    Returns:
        Dict with keys: status, response_time, message
    """
    key = key.strip()

    # --- PEM private key for asymmetric JWT algorithms ---
    if key.startswith("-----BEGIN"):
        begin_match = re.match(r"^-----BEGIN (.+?)-----", key)
        if begin_match is None:
            return {
                "status": "invalid",
                "response_time": 0,
                "message": "Malformed PEM header: could not parse BEGIN marker",
            }

        pem_type = begin_match.group(1)

        if pem_type not in _JWT_PEM_TYPES:
            return {
                "status": "invalid",
                "response_time": 0,
                "message": f"Unsupported PEM type for JWT signing: '{pem_type}'. "
                f"Expected one of: {', '.join(_JWT_PEM_TYPES)}",
            }

        expected_end = f"-----END {pem_type}-----"
        if expected_end not in key:
            return {
                "status": "invalid",
                "response_time": 0,
                "message": f"PEM structure invalid: missing '{expected_end}' marker",
            }

        return {
            "status": "format_valid",
            "response_time": 0,
            "message": f"Detected PEM-formatted JWT signing key ({pem_type})",
        }

    # --- Shared secret for symmetric JWT algorithms (HS256, etc.) ---
    if len(key) < 32:
        return {
            "status": "invalid",
            "response_time": 0,
            "message": "JWT secret must be at least 32 characters for adequate security",
        }

    return {
        "status": "format_valid",
        "response_time": 0,
        "message": f"Detected JWT shared secret ({len(key)} characters)",
    }
