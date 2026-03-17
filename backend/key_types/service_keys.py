"""
Service credential patterns and validators for KeyForge.

Supports CI/CD secrets (GitHub Actions, CircleCI, GitLab CI),
encryption keys, OAuth tokens, and communication APIs (Twilio, SendGrid).
"""

import re
import base64
import logging
import requests
from typing import Dict


logger = logging.getLogger("keyforge.validators")


# ---------------------------------------------------------------------------
# Detection patterns (matches API_PATTERNS format from backend/patterns.py)
# ---------------------------------------------------------------------------

SERVICE_PATTERNS = {
    "github_actions": {
        "name": "GitHub Actions",
        "category": "CI/CD",
        "patterns": [
            r"secrets\.",
            r"GITHUB_TOKEN",
            r"ACTIONS_RUNTIME_TOKEN",
            r"\$\{\{ secrets\.",
            r"github\.token",
        ],
        "files": [".yml", ".yaml"],
        "auth_type": "token",
        "scopes": ["workflows", "deployments", "packages", "environments"],
    },
    "circleci": {
        "name": "CircleCI",
        "category": "CI/CD",
        "patterns": [
            r"CIRCLE_TOKEN",
            r"circleci",
            r"\.circleci/config",
            r"CIRCLECI",
        ],
        "files": [".yml", ".yaml", ".env", ".sh"],
        "auth_type": "token",
        "scopes": ["pipelines", "workflows", "orbs"],
    },
    "gitlab_ci": {
        "name": "GitLab CI",
        "category": "CI/CD",
        "patterns": [
            r"GITLAB_TOKEN",
            r"CI_JOB_TOKEN",
            r"GL_TOKEN",
            r"gitlab-ci",
            r"GITLAB_PRIVATE_TOKEN",
        ],
        "files": [".yml", ".yaml", ".env", ".sh"],
        "auth_type": "token",
        "scopes": ["pipelines", "registry", "deployments"],
    },
    "encryption": {
        "name": "Encryption",
        "category": "Encryption",
        "patterns": [
            r"AES_KEY",
            r"ENCRYPTION_KEY",
            r"MASTER_KEY",
            r"DATA_KEY",
            r"KMS_KEY_ID",
            r"BEGIN ENCRYPTED",
            r"VAULT_TOKEN",
            r"vault_token",
        ],
        "files": [".py", ".js", ".ts", ".env", ".yml", ".yaml", ".json", ".conf"],
        "auth_type": "symmetric_key",
        "scopes": ["encrypt", "decrypt", "key_management"],
    },
    "oauth_generic": {
        "name": "OAuth Generic",
        "category": "OAuth",
        "patterns": [
            r"CLIENT_ID",
            r"CLIENT_SECRET",
            r"OAUTH_TOKEN",
            r"REFRESH_TOKEN",
            r"ACCESS_TOKEN",
            r"oauth2",
            r"authorization_code",
            r"client_credentials",
        ],
        "files": [".py", ".js", ".ts", ".env", ".yml", ".yaml", ".json"],
        "auth_type": "oauth2",
        "scopes": ["authorization", "token_exchange", "refresh"],
    },
    "twilio": {
        "name": "Twilio",
        "category": "Communication",
        "patterns": [
            r"TWILIO_ACCOUNT_SID",
            r"TWILIO_AUTH_TOKEN",
            r"twilio",
            r"AC[a-f0-9]{32}",
        ],
        "files": [".py", ".js", ".ts", ".env", ".yml", ".yaml"],
        "auth_type": "api_key",
        "scopes": ["sms", "voice", "video", "messaging"],
    },
    "sendgrid": {
        "name": "SendGrid",
        "category": "Communication",
        "patterns": [
            r"SENDGRID_API_KEY",
            r"SG\.",
            r"sendgrid",
            r"@sendgrid/mail",
        ],
        "files": [".py", ".js", ".ts", ".env", ".yml", ".yaml"],
        "auth_type": "api_key",
        "scopes": ["email_send", "templates", "contacts"],
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_hex_string(value: str) -> bool:
    """Return True if *value* consists entirely of hexadecimal characters."""
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def _is_base64_string(value: str) -> bool:
    """Return True if *value* is a valid base64-encoded string."""
    try:
        decoded = base64.b64decode(value, validate=True)
        # Re-encode to confirm round-trip consistency
        return base64.b64encode(decoded).decode() == value
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Validators (return dict matching validate_credential response format)
# ---------------------------------------------------------------------------

def validate_github_actions(key: str) -> dict:
    """Validate a GitHub Actions token format.

    Accepts tokens with a ``ghp_`` prefix or a ``v1.`` prefix and requires
    a minimum length of 20 characters.
    """
    if len(key) < 20:
        return {
            "status": "invalid",
            "response_time": 0,
            "message": "GitHub Actions token must be at least 20 characters",
        }

    if not (key.startswith("ghp_") or key.startswith("v1.")):
        return {
            "status": "invalid",
            "response_time": 0,
            "message": "GitHub Actions token must start with 'ghp_' or 'v1.' prefix",
        }

    return {
        "status": "format_valid",
        "response_time": 0,
        "message": "GitHub Actions token format is valid.",
    }


def validate_circleci(key: str) -> dict:
    """Validate a CircleCI token format (minimum 40 characters)."""
    if len(key) < 40:
        return {
            "status": "invalid",
            "response_time": 0,
            "message": "CircleCI token must be at least 40 characters",
        }

    return {
        "status": "format_valid",
        "response_time": 0,
        "message": "CircleCI token format is valid.",
    }


def validate_gitlab_ci(key: str) -> dict:
    """Validate a GitLab CI token format.

    Accepts tokens with a ``glpat-`` prefix or any token at least 20
    characters long.
    """
    if key.startswith("glpat-"):
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": "GitLab CI token format is valid (glpat- prefix detected).",
        }

    if len(key) < 20:
        return {
            "status": "invalid",
            "response_time": 0,
            "message": "GitLab CI token must start with 'glpat-' or be at least 20 characters",
        }

    return {
        "status": "format_valid",
        "response_time": 0,
        "message": "GitLab CI token format is valid.",
    }


def validate_encryption(key: str) -> dict:
    """Validate an encryption key or Vault token.

    Recognises:
    * Hex strings of 32+ characters (e.g. AES-128/256 keys).
    * Base64 strings of 24+ characters.
    * HashiCorp Vault tokens (``hvs.`` or ``s.`` prefix).
    """
    # Vault token check
    if key.startswith("hvs.") or key.startswith("s."):
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": "HashiCorp Vault token detected.",
        }

    # Hex string check (32+ chars)
    if len(key) >= 32 and _is_hex_string(key):
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": "Valid hex encryption key detected (32+ characters).",
        }

    # Base64 string check (24+ chars)
    if len(key) >= 24 and _is_base64_string(key):
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": "Valid base64 encryption key detected (24+ characters).",
        }

    return {
        "status": "invalid",
        "response_time": 0,
        "message": "Encryption key must be a hex string (32+ chars), "
                   "base64 string (24+ chars), or a Vault token (hvs./s. prefix)",
    }


def validate_oauth_generic(key: str) -> dict:
    """Validate a generic OAuth token (minimum 10 characters)."""
    if len(key) < 10:
        return {
            "status": "invalid",
            "response_time": 0,
            "message": "OAuth token must be at least 10 characters",
        }

    return {
        "status": "format_valid",
        "response_time": 0,
        "message": "OAuth token format is valid.",
    }


def validate_twilio(key: str) -> dict:
    """Validate a Twilio Account SID or Auth Token.

    Format checks:
    * Account SID: starts with ``AC``, 34 hex characters total.
    * Auth Token: exactly 32 hex characters.

    If the key looks like an Account SID, a live validation attempt is made
    against the Twilio API using the SID as both the username and password
    (which will fail auth but confirms the SID exists if 401 is returned).
    """
    # Account SID check
    if key.startswith("AC") and len(key) == 34:
        if _is_hex_string(key[2:]):
            # Attempt live validation
            try:
                response = requests.get(
                    f"https://api.twilio.com/2010-04-01/Accounts/{key}.json",
                    auth=(key, ""),
                    timeout=10,
                )
                elapsed_ms = int(response.elapsed.total_seconds() * 1000)

                if response.status_code == 200:
                    return {
                        "status": "active",
                        "response_time": elapsed_ms,
                        "message": "Twilio Account SID validated successfully.",
                    }
                elif response.status_code == 401:
                    return {
                        "status": "format_valid",
                        "response_time": elapsed_ms,
                        "message": "Twilio Account SID format is valid (auth token required for full validation).",
                    }
                else:
                    return {
                        "status": "format_valid",
                        "response_time": elapsed_ms,
                        "message": f"Twilio Account SID format is valid but API returned status {response.status_code}.",
                    }
            except Exception:
                logger.warning("Error during Twilio live validation")
                return {
                    "status": "format_valid",
                    "response_time": 0,
                    "message": "Twilio Account SID format is valid. Live validation could not be completed.",
                }

        return {
            "status": "invalid",
            "response_time": 0,
            "message": "Twilio Account SID must be 'AC' followed by 32 hex characters",
        }

    # Auth Token check (32 hex chars)
    if len(key) == 32 and _is_hex_string(key):
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": "Twilio Auth Token format is valid (32 hex characters).",
        }

    return {
        "status": "invalid",
        "response_time": 0,
        "message": "Twilio credential must be an Account SID (AC + 32 hex chars) "
                   "or an Auth Token (32 hex chars)",
    }


def validate_sendgrid(key: str) -> dict:
    """Validate a SendGrid API key.

    Format check: key must start with ``SG.`` and be at least 50 characters.

    Live validation: sends a GET request to the SendGrid scopes endpoint
    with Bearer authentication.
    """
    if not key.startswith("SG."):
        return {
            "status": "invalid",
            "response_time": 0,
            "message": "SendGrid API key must start with 'SG.'",
        }

    if len(key) < 50:
        return {
            "status": "invalid",
            "response_time": 0,
            "message": "SendGrid API key must be at least 50 characters",
        }

    # Attempt live validation
    try:
        response = requests.get(
            "https://api.sendgrid.com/v3/scopes",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10,
        )
        elapsed_ms = int(response.elapsed.total_seconds() * 1000)

        if response.status_code == 200:
            return {
                "status": "active",
                "response_time": elapsed_ms,
                "message": "SendGrid API key validated successfully.",
            }
        elif response.status_code == 401:
            return {
                "status": "invalid",
                "response_time": elapsed_ms,
                "message": "SendGrid API key is invalid (unauthorized).",
            }
        elif response.status_code == 403:
            return {
                "status": "format_valid",
                "response_time": elapsed_ms,
                "message": "SendGrid API key format is valid but lacks scopes permission.",
            }
        else:
            return {
                "status": "format_valid",
                "response_time": elapsed_ms,
                "message": f"SendGrid API key format is valid but API returned status {response.status_code}.",
            }
    except Exception:
        logger.warning("Error during SendGrid live validation")
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": "SendGrid API key format is valid. Live validation could not be completed.",
        }


# ---------------------------------------------------------------------------
# Registry dicts (mirror the FORMAT_VALIDATORS layout in validators.py)
# ---------------------------------------------------------------------------

SERVICE_FORMAT_VALIDATORS = {
    "github_actions": validate_github_actions,
    "circleci": validate_circleci,
    "gitlab_ci": validate_gitlab_ci,
    "encryption": validate_encryption,
    "oauth_generic": validate_oauth_generic,
    "twilio": validate_twilio,
    "sendgrid": validate_sendgrid,
}

SERVICE_LIVE_VALIDATORS = {
    "twilio": validate_twilio,
    "sendgrid": validate_sendgrid,
}
