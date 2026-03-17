"""
Cloud IAM credential patterns and validators for AWS, GCP, and Azure.
Supports detection and format validation of cloud provider credentials.
"""

import json
import re
import logging
from typing import Dict

logger = logging.getLogger("keyforge.cloud_keys")


# ---------------------------------------------------------------------------
# Cloud API Detection Patterns
# ---------------------------------------------------------------------------

CLOUD_PATTERNS = {
    "aws": {
        "name": "AWS",
        "category": "Cloud",
        "patterns": [
            r"AWS_ACCESS_KEY_ID",
            r"AWS_SECRET_ACCESS_KEY",
            r"AWS_SESSION_TOKEN",
            r"AKIA[0-9A-Z]{16}",
            r"aws_access_key",
            r"boto3",
            r"aws-sdk",
            r"@aws-sdk",
        ],
        "files": [".py", ".js", ".ts", ".env", ".yml", ".yaml", ".json", ".tf", ".cfg"],
        "auth_type": "access_key",
        "scopes": ["s3", "ec2", "lambda", "iam", "dynamodb", "sqs", "sns"],
    },
    "gcp": {
        "name": "GCP",
        "category": "Cloud",
        "patterns": [
            r"GOOGLE_APPLICATION_CREDENTIALS",
            r"GOOGLE_CLOUD_PROJECT",
            r"gcloud",
            r"google-cloud-",
            r"service_account.*private_key",
            r"type.*service_account",
        ],
        "files": [".py", ".js", ".ts", ".env", ".yml", ".yaml", ".json"],
        "auth_type": "service_account",
        "scopes": ["compute", "storage", "bigquery", "pubsub", "functions"],
    },
    "azure": {
        "name": "Azure",
        "category": "Cloud",
        "patterns": [
            r"AZURE_CLIENT_ID",
            r"AZURE_CLIENT_SECRET",
            r"AZURE_TENANT_ID",
            r"AZURE_SUBSCRIPTION_ID",
            r"azure-identity",
            r"DefaultAzureCredential",
            r"@azure/",
        ],
        "files": [".py", ".js", ".ts", ".env", ".yml", ".yaml", ".json"],
        "auth_type": "client_credentials",
        "scopes": ["compute", "storage", "keyvault", "sql", "functions"],
    },
}


# ---------------------------------------------------------------------------
# Format Validators
# ---------------------------------------------------------------------------

# Regex for base64-ish characters used in AWS secret access keys
_AWS_SECRET_RE = re.compile(r"^[A-Za-z0-9/+=]{40}$")

# Regex for GUID / UUID format used by Azure (8-4-4-4-12 hex)
_GUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

_GCP_SERVICE_ACCOUNT_REQUIRED_FIELDS = {"project_id", "private_key", "client_email"}


def validate_aws(key: str) -> dict:
    """Validate an AWS credential string.

    Supports:
    - Access key ID (starts with AKIA, 20 chars)
    - Secret access key (40 base64-ish chars)
    - Combined format ``ACCESS_KEY_ID:SECRET_ACCESS_KEY``

    Returns a dict with ``status`` and ``message``.
    """
    # Combined format: AKIAXXXXXXXXXXXXXXXX:secret
    if ":" in key:
        parts = key.split(":", 1)
        access_result = _validate_aws_access_key_id(parts[0])
        secret_result = _validate_aws_secret_access_key(parts[1])
        errors = []
        if access_result is not None:
            errors.append(f"access_key_id: {access_result}")
        if secret_result is not None:
            errors.append(f"secret_access_key: {secret_result}")
        if errors:
            return {
                "status": "invalid",
                "response_time": 0,
                "message": f"Invalid key format: {'; '.join(errors)}",
            }
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": "AWS access key ID and secret access key formats are valid.",
        }

    # Standalone access key ID
    if key.startswith("AKIA"):
        error = _validate_aws_access_key_id(key)
        if error:
            return {"status": "invalid", "response_time": 0, "message": f"Invalid key format: {error}"}
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": "AWS access key ID format is valid.",
        }

    # Standalone secret access key
    if _AWS_SECRET_RE.match(key):
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": "AWS secret access key format is valid.",
        }

    # Fallback – unable to determine type
    return {
        "status": "invalid",
        "response_time": 0,
        "message": (
            "Invalid key format: key does not match AWS access key ID (AKIA + 16 chars) "
            "or secret access key (40 base64 chars) patterns."
        ),
    }


def _validate_aws_access_key_id(key: str) -> str | None:
    """Return an error string if *key* is not a valid AWS access key ID, else None."""
    if not key.startswith("AKIA"):
        return "AWS access key IDs must start with 'AKIA'"
    if len(key) != 20:
        return "AWS access key IDs must be exactly 20 characters"
    if not re.match(r"^AKIA[0-9A-Z]{16}$", key):
        return "AWS access key IDs must be 'AKIA' followed by 16 uppercase alphanumeric characters"
    return None


def _validate_aws_secret_access_key(key: str) -> str | None:
    """Return an error string if *key* is not a valid AWS secret access key, else None."""
    if len(key) != 40:
        return "AWS secret access keys must be exactly 40 characters"
    if not _AWS_SECRET_RE.match(key):
        return "AWS secret access keys must contain only base64 characters (A-Z, a-z, 0-9, /, +, =)"
    return None


def validate_gcp(key: str) -> dict:
    """Validate a GCP credential string.

    Supports:
    - JSON service-account key (checks required fields)
    - Opaque key string (minimum length check)

    Returns a dict with ``status`` and ``message``.
    """
    # Attempt to parse as JSON service account key
    stripped = key.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            return {
                "status": "invalid",
                "response_time": 0,
                "message": "Invalid key format: key looks like JSON but could not be parsed.",
            }

        if data.get("type") != "service_account":
            return {
                "status": "invalid",
                "response_time": 0,
                "message": "Invalid key format: JSON 'type' field must be 'service_account'.",
            }

        missing = _GCP_SERVICE_ACCOUNT_REQUIRED_FIELDS - set(data.keys())
        if missing:
            return {
                "status": "invalid",
                "response_time": 0,
                "message": f"Invalid key format: missing required fields: {', '.join(sorted(missing))}.",
            }

        return {
            "status": "format_valid",
            "response_time": 0,
            "message": "GCP service account JSON format is valid.",
        }

    # Opaque key string – just check minimum length
    if len(key) < 10:
        return {
            "status": "invalid",
            "response_time": 0,
            "message": "Invalid key format: GCP key string is too short (minimum 10 characters).",
        }

    return {
        "status": "format_valid",
        "response_time": 0,
        "message": "GCP key string length is acceptable.",
    }


def validate_azure(key: str) -> dict:
    """Validate an Azure credential string.

    Supports:
    - GUID format for client_id / tenant_id (8-4-4-4-12 hex)
    - Client secret (minimum 30 characters)

    Returns a dict with ``status`` and ``message``.
    """
    # Check GUID format first
    if _GUID_RE.match(key):
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": "Azure GUID format is valid (client_id / tenant_id).",
        }

    # Treat as client secret – require 30+ chars
    if len(key) >= 30:
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": "Azure client secret length is acceptable.",
        }

    return {
        "status": "invalid",
        "response_time": 0,
        "message": (
            "Invalid key format: value is not a valid GUID (8-4-4-4-12 hex) "
            "and is too short for a client secret (minimum 30 characters)."
        ),
    }


# ---------------------------------------------------------------------------
# Registry dicts (mirrors the structure in validators.py)
# ---------------------------------------------------------------------------

CLOUD_FORMAT_VALIDATORS = {
    "aws": validate_aws,
    "gcp": validate_gcp,
    "azure": validate_azure,
}

# No cloud providers currently support live validation
CLOUD_LIVE_VALIDATORS: Dict[str, callable] = {}
