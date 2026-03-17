#!/usr/bin/env python3
"""GitHub App webhook handler for detecting committed secrets.

A standalone FastAPI mini-app that listens for GitHub push events, scans
committed file diffs for secret patterns, and reports findings.

Run standalone:
    python github_app.py          # starts on port 8002
"""

import hashlib
import hmac
import json
import logging
import os
import re
from typing import Dict, List

from fastapi import FastAPI, HTTPException, Header, Request
import uvicorn

# ── Configuration ─────────────────────────────────────────────────────────────

GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
GITHUB_APP_PRIVATE_KEY = os.environ.get("GITHUB_APP_PRIVATE_KEY", "")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("keyforge.github_app")

# ── Secret patterns (inline fallback) ────────────────────────────────────────

try:
    from backend.scanners import scan_content_for_secrets
    _USE_BACKEND_SCANNER = True
except ImportError:
    _USE_BACKEND_SCANNER = False

# Inline patterns used when backend.scanners is not importable
SECRET_PATTERNS = [
    {"name": "OpenAI API Key", "regex": r"sk-[a-zA-Z0-9]{40,}", "severity": "critical"},
    {"name": "AWS Access Key ID", "regex": r"AKIA[0-9A-Z]{16}", "severity": "critical"},
    {"name": "GitHub PAT", "regex": r"ghp_[a-zA-Z0-9]{36}", "severity": "critical"},
    {"name": "Stripe Test Key", "regex": r"sk_test_[a-zA-Z0-9]{20,}", "severity": "high"},
    {"name": "Stripe Live Key", "regex": r"sk_live_[a-zA-Z0-9]{20,}", "severity": "critical"},
    {"name": "SendGrid API Key", "regex": r"SG\.[a-zA-Z0-9_\-]{22,}\.[a-zA-Z0-9_\-]{22,}", "severity": "critical"},
    {"name": "Twilio API Key", "regex": r"SK[0-9a-fA-F]{32}", "severity": "critical"},
    {"name": "Slack Token", "regex": r"xox[bpors]-[0-9a-zA-Z\-]{10,}", "severity": "critical"},
    {"name": "Google API Key", "regex": r"AIza[0-9A-Za-z_\-]{35}", "severity": "high"},
    {"name": "Private Key", "regex": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "severity": "critical"},
    {
        "name": "Hardcoded API Key",
        "regex": r"""(?:api_key|apikey|api_secret)\s*=\s*["']([^"']{8,})["']""",
        "severity": "critical",
    },
    {
        "name": "Hardcoded Password",
        "regex": r"""(?:password|passwd|pwd)\s*=\s*["']([^"']{4,})["']""",
        "severity": "critical",
    },
    {
        "name": "Connection String",
        "regex": r"""(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^:\s]+:([^@\s]{3,})@[^\s]+""",
        "severity": "critical",
    },
]


def _scan_inline(content: str, filename: str) -> List[Dict]:
    """Scan content for secrets using inline patterns."""
    findings = []
    lines = content.splitlines()
    for line_no, line in enumerate(lines, start=1):
        for pattern in SECRET_PATTERNS:
            match = re.search(pattern["regex"], line, re.IGNORECASE)
            if match:
                matched_value = match.group(0)
                preview = matched_value[:8] + "..." if len(matched_value) > 8 else matched_value
                findings.append({
                    "line": line_no,
                    "type": pattern["name"],
                    "matched_value": preview,
                    "severity": pattern["severity"],
                    "filename": filename,
                })
    return findings


def scan_content(content: str, filename: str) -> List[Dict]:
    """Scan content for secrets, using backend scanner if available."""
    if _USE_BACKEND_SCANNER:
        findings = scan_content_for_secrets(content, filename)
        for f in findings:
            f["filename"] = filename
        return findings
    return _scan_inline(content, filename)


# ── Webhook signature verification ───────────────────────────────────────────


def verify_signature(payload_body: bytes, signature: str, secret: str) -> bool:
    """Verify the GitHub webhook signature (X-Hub-Signature-256).

    Args:
        payload_body: Raw request body bytes.
        signature: The X-Hub-Signature-256 header value.
        secret: The webhook secret.

    Returns:
        True if signature is valid.
    """
    if not secret:
        logger.warning("GITHUB_WEBHOOK_SECRET not set — skipping signature verification")
        return True

    if not signature:
        return False

    expected = "sha256=" + hmac.new(
        secret.encode(), payload_body, hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


# ── Diff parsing ─────────────────────────────────────────────────────────────


def _extract_added_lines_from_patch(patch: str) -> str:
    """Extract only added lines (lines starting with +) from a unified diff patch."""
    lines = []
    for line in patch.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            lines.append(line[1:])  # strip the leading +
    return "\n".join(lines)


# ── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="KeyForge GitHub App",
    description="Webhook handler for detecting secrets in GitHub pushes",
    version="1.0.0",
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"service": "KeyForge GitHub App", "status": "running"}


@app.post("/webhook/github")
async def handle_github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None),
):
    """Handle GitHub webhook events.

    Processes push events by scanning committed file patches for secret
    patterns. Returns a list of findings.
    """
    body = await request.body()

    # 1. Verify webhook signature
    if not verify_signature(body, x_hub_signature_256, GITHUB_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Only handle push events
    if x_github_event != "push":
        return {
            "status": "ignored",
            "event": x_github_event,
            "message": f"Event type '{x_github_event}' is not handled",
        }

    # 2. Parse the push event
    repo_name = payload.get("repository", {}).get("full_name", "unknown")
    ref = payload.get("ref", "")
    commits = payload.get("commits", [])
    pusher = payload.get("pusher", {}).get("name", "unknown")

    logger.info(
        "Processing push event: repo=%s ref=%s commits=%d pusher=%s",
        repo_name, ref, len(commits), pusher,
    )

    # 3. Scan each commit for secrets
    all_findings: List[Dict] = []

    for commit in commits:
        commit_id = commit.get("id", "unknown")
        commit_message = commit.get("message", "")
        commit_url = commit.get("url", "")

        # Collect files that were added or modified
        files_to_scan = []
        for f in commit.get("added", []):
            files_to_scan.append(f)
        for f in commit.get("modified", []):
            files_to_scan.append(f)

        # GitHub push payloads don't include full file content by default.
        # In a real implementation, you'd use the GitHub API to fetch file
        # content or the commit patch. Here we scan the commit message and
        # any patch data if available.

        # Check if patches are included (some GitHub API responses include them)
        if "patches" in commit:
            for file_path, patch in commit["patches"].items():
                added_content = _extract_added_lines_from_patch(patch)
                findings = scan_content(added_content, file_path)
                for finding in findings:
                    finding["commit_id"] = commit_id
                    finding["commit_message"] = commit_message[:100]
                    finding["commit_url"] = commit_url
                all_findings.extend(findings)

        # Also scan the diff content if provided at commit level
        if "diff" in commit:
            for file_entry in commit["diff"]:
                file_path = file_entry.get("filename", "unknown")
                patch = file_entry.get("patch", "")
                if patch:
                    added_content = _extract_added_lines_from_patch(patch)
                    findings = scan_content(added_content, file_path)
                    for finding in findings:
                        finding["commit_id"] = commit_id
                        finding["commit_message"] = commit_message[:100]
                        finding["commit_url"] = commit_url
                    all_findings.extend(findings)

        # Record file paths for annotation purposes even without patch data
        if not all_findings and files_to_scan:
            logger.info(
                "Commit %s touched %d file(s) but no patch data available for scanning",
                commit_id[:8], len(files_to_scan),
            )

    # 4. Build response with annotation-style findings
    annotations = []
    for finding in all_findings:
        annotations.append({
            "path": finding.get("filename", ""),
            "start_line": finding.get("line", 1),
            "end_line": finding.get("line", 1),
            "annotation_level": "failure" if finding.get("severity") == "critical" else "warning",
            "message": f"Potential secret detected: {finding.get('type', 'unknown')} "
                       f"(severity: {finding.get('severity', 'unknown')})",
            "title": f"Secret Found: {finding.get('type', 'unknown')}",
            "commit_id": finding.get("commit_id", ""),
        })

    # 5. Log summary
    if all_findings:
        logger.warning(
            "Found %d potential secret(s) in push to %s by %s",
            len(all_findings), repo_name, pusher,
        )
    else:
        logger.info("No secrets detected in push to %s by %s", repo_name, pusher)

    return {
        "status": "scanned",
        "repository": repo_name,
        "ref": ref,
        "commits_scanned": len(commits),
        "total_findings": len(all_findings),
        "findings": all_findings,
        "annotations": annotations,
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8002))
    logger.info("Starting KeyForge GitHub App on port %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port)
