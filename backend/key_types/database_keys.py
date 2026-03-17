"""
Database credential patterns and validators for KeyForge.

Supports PostgreSQL, MySQL, Redis, and MongoDB connection strings and passwords.
"""

from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Detection patterns (matches API_PATTERNS format from backend/patterns.py)
# ---------------------------------------------------------------------------

DATABASE_PATTERNS = {
    "postgresql": {
        "name": "PostgreSQL",
        "category": "Database",
        "patterns": [
            r"postgresql://",
            r"postgres://",
            r"POSTGRES_PASSWORD",
            r"PGPASSWORD",
            r"DATABASE_URL.*postgres",
            r"psycopg2",
            r"asyncpg",
            r"pg_connect",
        ],
        "files": [".py", ".js", ".ts", ".env", ".yml", ".yaml", ".json", ".conf"],
        "auth_type": "connection_string",
        "scopes": ["read", "write", "admin", "replication"],
    },
    "mysql": {
        "name": "MySQL",
        "category": "Database",
        "patterns": [
            r"mysql://",
            r"MYSQL_ROOT_PASSWORD",
            r"MYSQL_PASSWORD",
            r"mysql\.connector",
            r"pymysql",
            r"mysql2",
        ],
        "files": [".py", ".js", ".ts", ".env", ".yml", ".yaml", ".json", ".conf"],
        "auth_type": "connection_string",
        "scopes": ["read", "write", "admin", "replication"],
    },
    "redis": {
        "name": "Redis",
        "category": "Database",
        "patterns": [
            r"redis://",
            r"rediss://",
            r"REDIS_URL",
            r"REDIS_PASSWORD",
            r"redis\.Redis",
            r"ioredis",
            r"redis-cli",
        ],
        "files": [".py", ".js", ".ts", ".env", ".yml", ".yaml", ".json"],
        "auth_type": "connection_string",
        "scopes": ["read", "write", "pub_sub", "admin"],
    },
    "mongodb_cred": {
        "name": "MongoDB",
        "category": "Database",
        "patterns": [
            r"mongodb\+srv://",
            r"mongodb://.*:.*@",
            r"MONGO_PASSWORD",
            r"MONGODB_URI",
            r"mongoose\.connect",
        ],
        "files": [".py", ".js", ".ts", ".env", ".yml", ".yaml", ".json"],
        "auth_type": "connection_string",
        "scopes": ["read", "write", "admin", "replication"],
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_connection_string(key: str, expected_schemes: list[str]) -> dict | None:
    """Attempt to parse a URL-style connection string.

    Returns a dict with parsed components on success, or None if the key
    does not look like a connection string for the given schemes.
    """
    for scheme in expected_schemes:
        if key.startswith(scheme):
            try:
                parsed = urlparse(key)
                components = {}
                if parsed.hostname:
                    components["host"] = parsed.hostname
                if parsed.port:
                    components["port"] = parsed.port
                if parsed.username:
                    components["user"] = parsed.username
                if parsed.path and parsed.path != "/":
                    components["database"] = parsed.path.lstrip("/")
                return components
            except Exception:
                return {}
    return None


def _password_check(key: str, min_length: int = 8) -> str | None:
    """Return an error string if *key* is too short to be a password."""
    if len(key) < min_length:
        return f"Password must be at least {min_length} characters"
    return None


# ---------------------------------------------------------------------------
# Validators (return dict matching validate_credential response format)
# ---------------------------------------------------------------------------


def validate_postgresql(key: str) -> dict:
    """Validate a PostgreSQL connection string or password.

    No live validation is performed (would require database connectivity).
    """
    # Connection string check
    parsed = _parse_connection_string(key, ["postgresql://", "postgres://"])
    if parsed is not None:
        details = ", ".join(f"{k}={v}" for k, v in parsed.items()) if parsed else "minimal"
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": f"Valid PostgreSQL connection string detected ({details}). "
            "Live validation not available (requires database connectivity).",
        }

    # Plain password fallback
    err = _password_check(key)
    if err:
        return {
            "status": "invalid",
            "response_time": 0,
            "message": f"Invalid PostgreSQL credential: {err}",
        }

    return {
        "status": "format_valid",
        "response_time": 0,
        "message": "Value accepted as a PostgreSQL password (8+ characters). "
        "Live validation not available (requires database connectivity).",
    }


def validate_mysql(key: str) -> dict:
    """Validate a MySQL connection string or password.

    No live validation is performed (would require database connectivity).
    """
    parsed = _parse_connection_string(key, ["mysql://"])
    if parsed is not None:
        details = ", ".join(f"{k}={v}" for k, v in parsed.items()) if parsed else "minimal"
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": f"Valid MySQL connection string detected ({details}). "
            "Live validation not available (requires database connectivity).",
        }

    err = _password_check(key)
    if err:
        return {
            "status": "invalid",
            "response_time": 0,
            "message": f"Invalid MySQL credential: {err}",
        }

    return {
        "status": "format_valid",
        "response_time": 0,
        "message": "Value accepted as a MySQL password (8+ characters). "
        "Live validation not available (requires database connectivity).",
    }


def validate_redis(key: str) -> dict:
    """Validate a Redis connection string or password.

    No live validation is performed (would require database connectivity).
    """
    parsed = _parse_connection_string(key, ["redis://", "rediss://"])
    if parsed is not None:
        scheme = "rediss" if key.startswith("rediss://") else "redis"
        details = ", ".join(f"{k}={v}" for k, v in parsed.items()) if parsed else "minimal"
        tls_note = " (TLS enabled)" if scheme == "rediss" else ""
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": f"Valid Redis connection string detected{tls_note} ({details}). "
            "Live validation not available (requires database connectivity).",
        }

    err = _password_check(key)
    if err:
        return {
            "status": "invalid",
            "response_time": 0,
            "message": f"Invalid Redis credential: {err}",
        }

    return {
        "status": "format_valid",
        "response_time": 0,
        "message": "Value accepted as a Redis password (8+ characters). "
        "Live validation not available (requires database connectivity).",
    }


def validate_mongodb(key: str) -> dict:
    """Validate a MongoDB connection string or password.

    No live validation is performed (would require database connectivity).
    """
    parsed = _parse_connection_string(key, ["mongodb+srv://", "mongodb://"])
    if parsed is not None:
        srv = key.startswith("mongodb+srv://")
        details = ", ".join(f"{k}={v}" for k, v in parsed.items()) if parsed else "minimal"
        srv_note = " (SRV)" if srv else ""
        return {
            "status": "format_valid",
            "response_time": 0,
            "message": f"Valid MongoDB connection string detected{srv_note} ({details}). "
            "Live validation not available (requires database connectivity).",
        }

    err = _password_check(key)
    if err:
        return {
            "status": "invalid",
            "response_time": 0,
            "message": f"Invalid MongoDB credential: {err}",
        }

    return {
        "status": "format_valid",
        "response_time": 0,
        "message": "Value accepted as a MongoDB password (8+ characters). "
        "Live validation not available (requires database connectivity).",
    }


# ---------------------------------------------------------------------------
# Registry dicts (mirror the FORMAT_VALIDATORS layout in validators.py)
# ---------------------------------------------------------------------------

DATABASE_FORMAT_VALIDATORS = {
    "postgresql": validate_postgresql,
    "mysql": validate_mysql,
    "redis": validate_redis,
    "mongodb_cred": validate_mongodb,
}
