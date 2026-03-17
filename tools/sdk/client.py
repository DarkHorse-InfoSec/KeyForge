"""KeyForge Python SDK client."""

import json
from typing import List, Optional

import requests


class KeyForgeError(Exception):
    """Custom exception for KeyForge SDK errors."""

    def __init__(self, message: str, status_code: int = None, detail: str = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)

    def __str__(self):
        parts = [self.message]
        if self.status_code:
            parts.append(f"(HTTP {self.status_code})")
        if self.detail:
            parts.append(f"- {self.detail}")
        return " ".join(parts)


class KeyForgeClient:
    """Python SDK client for the KeyForge API.

    Usage::

        client = KeyForgeClient()
        client.login("myuser", "mypassword")
        creds = client.list_credentials()
    """

    def __init__(self, api_url: str = "http://localhost:8001", token: str = None):
        self.api_url = api_url.rstrip("/")
        self.token = token
        self._session = requests.Session()

    # ── Internal helpers ──────────────────────────────────────────────────

    def _headers(self) -> dict:
        """Return request headers with auth token if available."""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make an HTTP request and handle errors."""
        url = f"{self.api_url}{path}"
        headers = kwargs.pop("headers", {})
        headers.update(self._headers())

        try:
            resp = self._session.request(method, url, headers=headers, **kwargs)
        except requests.ConnectionError as exc:
            raise KeyForgeError(f"Connection failed to {self.api_url}") from exc
        except requests.Timeout as exc:
            raise KeyForgeError("Request timed out") from exc
        except requests.RequestException as exc:
            raise KeyForgeError(f"Request failed: {exc}") from exc

        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise KeyForgeError(
                f"API error on {method.upper()} {path}",
                status_code=resp.status_code,
                detail=str(detail),
            )

        return resp

    def _json(self, method: str, path: str, **kwargs):
        """Make a request and return parsed JSON."""
        resp = self._request(method, path, **kwargs)
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            return resp.json()
        return resp.text

    # ── Auth ──────────────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> str:
        """Authenticate and store the JWT token.

        Returns:
            The access token string.
        """
        data = self._json(
            "post",
            "/api/auth/login",
            data={"username": username, "password": password},
        )
        self.token = data["access_token"]
        return self.token

    # ── Credentials ───────────────────────────────────────────────────────

    def list_credentials(self, skip: int = 0, limit: int = 50) -> list:
        """List credentials with pagination.

        Returns:
            A list of credential dicts.
        """
        return self._json(
            "get",
            "/api/credentials",
            params={"skip": skip, "limit": limit},
        )

    def get_credential(self, credential_id: str) -> dict:
        """Get a single credential by ID.

        Returns:
            Credential dict.
        """
        return self._json("get", f"/api/credentials/{credential_id}")

    def create_credential(
        self,
        api_name: str,
        api_key: str,
        environment: str = "development",
    ) -> dict:
        """Create a new credential.

        Returns:
            The created credential dict.
        """
        return self._json(
            "post",
            "/api/credentials",
            json={"api_name": api_name, "api_key": api_key, "environment": environment},
        )

    def test_credential(self, credential_id: str) -> dict:
        """Test a credential against its API.

        Returns:
            Test result dict.
        """
        return self._json("post", f"/api/credentials/{credential_id}/test")

    def delete_credential(self, credential_id: str) -> dict:
        """Delete a credential.

        Returns:
            Deletion confirmation dict.
        """
        return self._json("delete", f"/api/credentials/{credential_id}")

    # ── Import / Export ───────────────────────────────────────────────────

    def export_env(self) -> str:
        """Export all credentials as .env file content.

        Returns:
            The .env formatted string.
        """
        resp = self._request("get", "/api/export/env")
        return resp.text

    def import_env(self, content: str) -> dict:
        """Import credentials from .env file content.

        Args:
            content: The .env file contents as a string.

        Returns:
            Import result dict with imported/skipped counts.
        """
        return self._json(
            "post",
            "/api/import/env",
            data=content,
            headers={"Content-Type": "text/plain"},
        )

    def export_json(self, include_keys: bool = False) -> list:
        """Export credentials as a JSON list.

        Args:
            include_keys: If True, include decrypted API keys.

        Returns:
            List of credential dicts.
        """
        resp = self._request(
            "get",
            "/api/export/json",
            params={"include_keys": str(include_keys).lower()},
        )
        return json.loads(resp.text)

    def import_json(self, entries: list) -> dict:
        """Import credentials from a JSON list.

        Args:
            entries: List of dicts with api_name, api_key, environment.

        Returns:
            Import result dict.
        """
        return self._json("post", "/api/import/json", json=entries)

    # ── Health ────────────────────────────────────────────────────────────

    def get_health(self) -> dict:
        """Check API health status.

        Returns:
            Health status dict.
        """
        return self._json("get", "/api/health")

    # ── Teams ─────────────────────────────────────────────────────────────

    def list_teams(self) -> list:
        """List teams the current user belongs to.

        Returns:
            List of team dicts.
        """
        return self._json("get", "/api/teams")

    # ── Health Checks ─────────────────────────────────────────────────────

    def run_health_checks(self) -> dict:
        """Run health checks for all credentials.

        Returns:
            Health check results dict.
        """
        return self._json("post", "/api/health-checks/run")
