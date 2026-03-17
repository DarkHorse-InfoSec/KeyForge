#!/usr/bin/env python3
"""Docker Compose credential injection helper for KeyForge."""

import argparse
import json
import os
import sys
from pathlib import Path

import requests
import yaml


def _headers(token: str) -> dict:
    """Return authorization headers."""
    return {"Authorization": f"Bearer {token}"}


def _fetch_env_content(api_url: str, token: str) -> str:
    """Pull .env content from the KeyForge API."""
    resp = requests.get(f"{api_url}/api/export/env", headers=_headers(token))
    resp.raise_for_status()
    return resp.text


def _parse_env_lines(content: str) -> dict:
    """Parse .env content into a dict of KEY=VALUE pairs (skipping comments)."""
    env_vars = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        env_vars[key.strip()] = value.strip()
    return env_vars


# ── Public API ────────────────────────────────────────────────────────────────


def generate_env_file(api_url: str, token: str, output_path: str = ".env") -> str:
    """Pull credentials from KeyForge and write them to a .env file.

    Args:
        api_url: The KeyForge API base URL.
        token: JWT auth token.
        output_path: Destination file path (default ".env").

    Returns:
        The path of the written file.
    """
    content = _fetch_env_content(api_url, token)
    Path(output_path).write_text(content)
    return output_path


def generate_docker_compose_override(
    api_url: str,
    token: str,
    service_names: list,
) -> str:
    """Generate a docker-compose.override.yml that maps credentials as env vars.

    Args:
        api_url: The KeyForge API base URL.
        token: JWT auth token.
        service_names: List of Docker Compose service names.

    Returns:
        The YAML string of the generated override file.
    """
    content = _fetch_env_content(api_url, token)
    env_vars = _parse_env_lines(content)

    # Build the environment list for each service
    env_list = [f"{k}={v}" for k, v in env_vars.items()]

    services = {}
    for name in service_names:
        services[name] = {"environment": env_list}

    override = {
        "version": "3.8",
        "services": services,
    }

    yaml_content = yaml.dump(override, default_flow_style=False, sort_keys=False)
    return yaml_content


def inject_to_running_container(
    container_name: str,
    api_url: str,
    token: str,
) -> str:
    """Generate a docker exec command to set env vars in a running container.

    This function prints the command but does NOT execute it.

    Args:
        container_name: Name or ID of the running Docker container.
        api_url: The KeyForge API base URL.
        token: JWT auth token.

    Returns:
        The generated docker exec command string.
    """
    content = _fetch_env_content(api_url, token)
    env_vars = _parse_env_lines(content)

    if not env_vars:
        cmd = f"# No credentials found to inject into {container_name}"
        print(cmd)
        return cmd

    # Build a series of -e flags for docker exec with env
    env_flags = " ".join(f"-e {k}='{v}'" for k, v in env_vars.items())
    cmd = f"docker exec {env_flags} {container_name} env"

    print(cmd)
    return cmd


# ── CLI entry point ───────────────────────────────────────────────────────────


def main():
    """Run the Docker integration tool from the command line."""
    parser = argparse.ArgumentParser(
        description="KeyForge Docker Compose credential injection helper",
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["pull", "override", "inject"],
        help="Action to perform: pull (.env), override (docker-compose.override.yml), inject (docker exec)",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8001",
        help="KeyForge API URL",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Auth token (or set KEYFORGE_TOKEN env var)",
    )
    parser.add_argument(
        "--service",
        default=None,
        help="Comma-separated list of Docker Compose service names",
    )
    parser.add_argument(
        "--container",
        default=None,
        help="Running container name (for inject action)",
    )
    parser.add_argument(
        "--output",
        default=".env",
        help="Output file path (default: .env)",
    )

    args = parser.parse_args()

    token = args.token or os.environ.get("KEYFORGE_TOKEN")
    if not token:
        print("Error: --token or KEYFORGE_TOKEN environment variable is required.")
        sys.exit(1)

    if args.action == "pull":
        path = generate_env_file(args.api_url, token, args.output)
        print(f"Credentials written to {path}")

    elif args.action == "override":
        if not args.service:
            print("Error: --service is required for override action.")
            sys.exit(1)
        service_names = [s.strip() for s in args.service.split(",")]
        yaml_content = generate_docker_compose_override(args.api_url, token, service_names)
        output_path = args.output if args.output != ".env" else "docker-compose.override.yml"
        Path(output_path).write_text(yaml_content)
        print(f"Override file written to {output_path}")

    elif args.action == "inject":
        if not args.container:
            print("Error: --container is required for inject action.")
            sys.exit(1)
        inject_to_running_container(args.container, args.api_url, token)


if __name__ == "__main__":
    main()
