"""SSH key detection patterns and validators for KeyForge."""

import re
import base64
import logging
from typing import Dict

logger = logging.getLogger("keyforge.ssh_keys")

# SSH Key Detection Patterns (matches API_PATTERNS format)
PATTERNS = {
    "ssh": {
        "name": "SSH",
        "category": "SSH",
        "patterns": [
            r"BEGIN OPENSSH PRIVATE KEY",
            r"BEGIN RSA PRIVATE KEY",
            r"BEGIN DSA PRIVATE KEY",
            r"BEGIN EC PRIVATE KEY",
            r"ssh-rsa",
            r"ssh-ed25519",
            r"ssh-ecdsa",
            r"id_rsa",
            r"id_ed25519",
            r"id_ecdsa",
            r"SSH_PRIVATE_KEY",
            r"SSH_KEY",
            r"DEPLOY_KEY",
        ],
        "files": [".py", ".js", ".ts", ".sh", ".yml", ".yaml", ".json", ".env", ".conf", ".cfg"],
        "auth_type": "private_key",
        "scopes": ["server_access", "git_operations", "deploy", "tunneling"],
    }
}

# PEM key types considered valid for SSH private keys
_VALID_PEM_TYPES = ("OPENSSH PRIVATE KEY", "RSA PRIVATE KEY", "DSA PRIVATE KEY", "EC PRIVATE KEY")

# Public key prefixes
_PUBLIC_KEY_PREFIXES = ("ssh-rsa", "ssh-ed25519", "ssh-ecdsa", "ecdsa-sha2-nistp")


def validate_ssh_key(key: str) -> Dict:
    """
    Validate an SSH key by inspecting its format.

    Checks PEM-formatted private keys for correct BEGIN/END markers and
    public keys for recognized prefixes and valid base64 content.
    No live validation is performed because SSH keys cannot be tested
    without a target host.

    Returns:
        Dict with keys: status, response_time, message
    """
    key = key.strip()

    # --- PEM private key detection ---
    if key.startswith("-----BEGIN"):
        # Extract the key type from the BEGIN marker
        begin_match = re.match(r"^-----BEGIN (.+?)-----", key)
        if begin_match is None:
            return {
                "status": "invalid",
                "response_time": 0,
                "message": "Malformed PEM header: could not parse BEGIN marker",
            }

        pem_type = begin_match.group(1)

        if pem_type not in _VALID_PEM_TYPES:
            return {
                "status": "invalid",
                "response_time": 0,
                "message": f"Unrecognized SSH key type: '{pem_type}'. "
                           f"Expected one of: {', '.join(_VALID_PEM_TYPES)}",
            }

        # Verify matching END marker
        expected_end = f"-----END {pem_type}-----"
        if expected_end not in key:
            return {
                "status": "invalid",
                "response_time": 0,
                "message": f"PEM structure invalid: missing '{expected_end}' marker",
            }

        # Validate that the body between markers is non-empty
        body_match = re.search(
            rf"-----BEGIN {re.escape(pem_type)}-----\s*(.+?)\s*-----END {re.escape(pem_type)}-----",
            key,
            re.DOTALL,
        )
        if body_match is None or not body_match.group(1).strip():
            return {
                "status": "invalid",
                "response_time": 0,
                "message": "PEM key body is empty",
            }

        return {
            "status": "format_valid",
            "response_time": 0,
            "message": f"Detected valid PEM-formatted SSH private key ({pem_type})",
        }

    # --- Public key detection ---
    for prefix in _PUBLIC_KEY_PREFIXES:
        if key.startswith(prefix):
            parts = key.split()
            if len(parts) < 2:
                return {
                    "status": "invalid",
                    "response_time": 0,
                    "message": f"Public key starts with '{prefix}' but is missing the base64 data",
                }

            b64_data = parts[1]
            try:
                decoded = base64.b64decode(b64_data, validate=True)
                if len(decoded) < 16:
                    return {
                        "status": "invalid",
                        "response_time": 0,
                        "message": "Base64 content decoded but appears too short to be a valid key",
                    }
            except Exception:
                return {
                    "status": "invalid",
                    "response_time": 0,
                    "message": "Public key contains invalid base64 content",
                }

            comment = parts[2] if len(parts) > 2 else None
            msg = f"Detected valid SSH public key ({prefix})"
            if comment:
                msg += f" with comment '{comment}'"

            return {
                "status": "format_valid",
                "response_time": 0,
                "message": msg,
            }

    return {
        "status": "invalid",
        "response_time": 0,
        "message": "Unrecognized SSH key format. Expected a PEM private key or an OpenSSH public key.",
    }
