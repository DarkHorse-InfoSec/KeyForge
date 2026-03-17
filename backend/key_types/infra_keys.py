"""
Infrastructure key patterns and validators for KeyForge.
Covers TLS/SSL certificates and container registry credentials.
"""

import base64
import logging
import re
from typing import Dict

import requests

logger = logging.getLogger("keyforge.infra_keys")

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

INFRA_PATTERNS = {
    "tls_ssl": {
        "name": "TLS/SSL",
        "category": "Infrastructure",
        "patterns": [
            r"BEGIN CERTIFICATE",
            r"BEGIN PRIVATE KEY",
            r"SSL_CERT",
            r"SSL_KEY",
            r"TLS_CERT",
            r"TLS_KEY",
            r"\.pem",
            r"\.crt",
            r"\.key",
            r"ssl_certificate",
            r"ssl_certificate_key",
        ],
        "files": [".py", ".js", ".conf", ".yml", ".yaml", ".env", ".nginx", ".tf"],
        "auth_type": "certificate",
        "scopes": ["https", "mtls", "service_mesh", "api_gateway"],
    },
    "docker_hub": {
        "name": "Docker Hub",
        "category": "Container Registry",
        "patterns": [
            r"DOCKER_PASSWORD",
            r"DOCKER_TOKEN",
            r"DOCKER_USERNAME",
            r"docker login",
            r"docker\.io",
            r"DOCKERHUB_TOKEN",
        ],
        "files": [".sh", ".yml", ".yaml", ".env", ".json", ".Dockerfile"],
        "auth_type": "token",
        "scopes": ["pull", "push", "admin"],
    },
    "aws_ecr": {
        "name": "AWS ECR",
        "category": "Container Registry",
        "patterns": [
            r"\.dkr\.ecr\.",
            r"ecr:GetAuthorizationToken",
            r"ECR_REGISTRY",
            r"aws ecr get-login",
        ],
        "files": [".sh", ".yml", ".yaml", ".env", ".json", ".tf"],
        "auth_type": "iam",
        "scopes": ["pull", "push", "admin"],
    },
    "ghcr": {
        "name": "GitHub Container Registry",
        "category": "Container Registry",
        "patterns": [
            r"ghcr\.io",
            r"GITHUB_TOKEN.*ghcr",
            r"CR_PAT",
            r"container-registry.*github",
        ],
        "files": [".sh", ".yml", ".yaml", ".env", ".json"],
        "auth_type": "token",
        "scopes": ["pull", "push", "delete"],
    },
}

# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

_BASE64_RE = re.compile(r"^[A-Za-z0-9+/=\s]+$")


def validate_tls_ssl(key: str) -> Dict:
    """Validate a TLS/SSL certificate or private key in PEM format.

    Checks for proper BEGIN/END markers and base64-encoded content between them.
    """
    key = key.strip()

    # Detect type based on BEGIN marker
    if "-----BEGIN CERTIFICATE-----" in key:
        pem_type = "certificate"
        begin_marker = "-----BEGIN CERTIFICATE-----"
        end_marker = "-----END CERTIFICATE-----"
    elif "-----BEGIN PRIVATE KEY-----" in key:
        pem_type = "private_key"
        begin_marker = "-----BEGIN PRIVATE KEY-----"
        end_marker = "-----END PRIVATE KEY-----"
    else:
        return {
            "status": "invalid",
            "response_time": 0,
            "message": "PEM data must contain '-----BEGIN CERTIFICATE-----' or '-----BEGIN PRIVATE KEY-----'",
        }

    # Verify matching END marker
    if end_marker not in key:
        return {
            "status": "invalid",
            "response_time": 0,
            "message": f"Missing matching end marker: {end_marker}",
        }

    # Extract and validate base64 content between markers
    start_idx = key.index(begin_marker) + len(begin_marker)
    end_idx = key.index(end_marker)
    body = key[start_idx:end_idx].strip()

    if not body:
        return {
            "status": "invalid",
            "response_time": 0,
            "message": "PEM body is empty",
        }

    if not _BASE64_RE.match(body):
        return {
            "status": "invalid",
            "response_time": 0,
            "message": "PEM body contains invalid base64 characters",
        }

    # Try actual base64 decode as a final sanity check
    try:
        base64.b64decode(body)
    except Exception:
        return {
            "status": "invalid",
            "response_time": 0,
            "message": "PEM body is not valid base64",
        }

    return {
        "status": "format_valid",
        "response_time": 0,
        "message": f"Valid PEM format detected (type: {pem_type})",
    }


def validate_docker_hub(key: str) -> Dict:
    """Validate a Docker Hub token.

    Checks minimum length (UUID or access-token format) and optionally
    performs a live validation against the Docker Hub API.
    """
    key = key.strip()

    if len(key) < 36:
        return {
            "status": "invalid",
            "response_time": 0,
            "message": "Docker Hub token must be at least 36 characters",
        }

    # Live validation
    try:
        response = requests.get(
            "https://hub.docker.com/v2/repositories/library/alpine/",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10,
        )
        elapsed_ms = int(response.elapsed.total_seconds() * 1000)

        if response.status_code == 200:
            return {
                "status": "active",
                "response_time": elapsed_ms,
                "message": "Credential validated successfully",
            }
        elif response.status_code == 401:
            return {
                "status": "invalid",
                "response_time": elapsed_ms,
                "message": "Invalid token (unauthorized)",
            }
        else:
            return {
                "status": "format_valid",
                "response_time": elapsed_ms,
                "message": f"Token format is valid but API returned status {response.status_code}",
            }
    except Exception:
        logger.debug("Docker Hub live validation failed, falling back to format check")
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": "Token format is valid but could not reach Docker Hub API",
        }


def validate_aws_ecr(key: str) -> Dict:
    """Validate an AWS ECR credential (format check only).

    ECR relies on AWS IAM for authentication, so standalone credential
    validation is not possible without full AWS context.
    """
    return {
        "status": "format_valid",
        "response_time": 0,
        "message": "AWS ECR uses IAM authentication; standalone validation is not supported",
    }


def validate_ghcr(key: str) -> Dict:
    """Validate a GitHub Container Registry token.

    Checks token format (ghp_ prefix or generic token) and optionally
    performs live validation against the GHCR API.
    """
    key = key.strip()

    # Format check: accept ghp_ prefixed tokens or generic tokens
    if not (key.startswith("ghp_") or re.match(r"^[A-Za-z0-9_-]{20,}$", key)):
        return {
            "status": "invalid",
            "response_time": 0,
            "message": "GHCR token should start with 'ghp_' or be a valid alphanumeric token",
        }

    # Live validation
    try:
        response = requests.get(
            "https://ghcr.io/v2/",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10,
        )
        elapsed_ms = int(response.elapsed.total_seconds() * 1000)

        if response.status_code == 200:
            return {
                "status": "active",
                "response_time": elapsed_ms,
                "message": "Credential validated successfully",
            }
        elif response.status_code == 401:
            return {
                "status": "invalid",
                "response_time": elapsed_ms,
                "message": "Invalid token (unauthorized)",
            }
        else:
            return {
                "status": "format_valid",
                "response_time": elapsed_ms,
                "message": f"Token format is valid but API returned status {response.status_code}",
            }
    except Exception:
        logger.debug("GHCR live validation failed, falling back to format check")
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": "Token format is valid but could not reach GHCR API",
        }


# ---------------------------------------------------------------------------
# Registries for integration with the core KeyForge system
# ---------------------------------------------------------------------------

FORMAT_VALIDATORS = {
    "tls_ssl": validate_tls_ssl,
    "docker_hub": validate_docker_hub,
    "aws_ecr": validate_aws_ecr,
    "ghcr": validate_ghcr,
}

LIVE_VALIDATORS = {
    "docker_hub": validate_docker_hub,
    "ghcr": validate_ghcr,
}

LIVE_VALIDATION_PROVIDERS = set(LIVE_VALIDATORS.keys())
