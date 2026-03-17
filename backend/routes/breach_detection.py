"""Breach detection routes for KeyForge."""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
import hashlib
import uuid

try:
    from ..config import db, logger
    from ..security import get_current_user, decrypt_api_key
    from ..models_analytics import BreachCheckResult, BreachCheckResponse
except ImportError:
    from backend.config import db, logger
    from backend.security import get_current_user, decrypt_api_key
    from backend.models_analytics import BreachCheckResult, BreachCheckResponse

router = APIRouter(prefix="/api", tags=["breach-detection"])

# Known compromised patterns
COMPROMISED_PATTERNS = [
    "sk-test", "test123", "password", "123456", "secret",
    "api_key", "changeme", "default", "example", "dummy",
]


def _hash_key(key: str) -> str:
    """Hash a key with SHA-256 for safe comparison."""
    return hashlib.sha256(key.encode()).hexdigest()


def _check_compromised_patterns(decrypted_key: str) -> dict:
    """Check a decrypted key against known compromised patterns.

    Returns a dict with is_compromised, sources_checked, and details.
    """
    sources_checked = []
    issues = []

    # Check 1: Short keys (less than 8 chars)
    sources_checked.append("key_length_check")
    if len(decrypted_key) < 8:
        issues.append("Key is too short (less than 8 characters)")

    # Check 2: Common test/compromised patterns
    sources_checked.append("known_patterns_check")
    lower_key = decrypted_key.lower()
    for pattern in COMPROMISED_PATTERNS:
        if pattern in lower_key:
            issues.append(f"Key contains known compromised pattern: '{pattern}'")
            break

    # Check 3: All same character
    sources_checked.append("entropy_check")
    if len(set(decrypted_key)) == 1:
        issues.append("Key consists of a single repeated character")

    # Check 4: Decryption failure
    sources_checked.append("decryption_check")
    if decrypted_key == "[decryption failed]":
        issues.append("Key could not be decrypted — may be corrupted")

    is_compromised = len(issues) > 0
    details = "; ".join(issues) if issues else "No issues found"

    return {
        "is_compromised": is_compromised,
        "sources_checked": sources_checked,
        "details": details,
    }


async def _check_hash_collision(key_hash: str, user_id: str, credential_id: str) -> str | None:
    """Check if the same key hash exists in another user's credentials."""
    all_credentials = await db.credentials.find(
        {"user_id": {"$ne": user_id}}
    ).to_list(1000)

    for cred in all_credentials:
        other_decrypted = decrypt_api_key(cred.get("api_key", ""))
        if other_decrypted == "[decryption failed]":
            continue
        other_hash = _hash_key(other_decrypted)
        if other_hash == key_hash:
            return "Key hash matches a credential belonging to another user — possible credential reuse or leak"
    return None


async def _run_breach_check(credential_id: str, user_id: str) -> BreachCheckResponse:
    """Run a full breach check on a single credential."""
    credential = await db.credentials.find_one({
        "id": credential_id,
        "user_id": user_id,
    })
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    decrypted_key = decrypt_api_key(credential.get("api_key", ""))
    result = _check_compromised_patterns(decrypted_key)

    # Cross-user hash comparison
    if decrypted_key != "[decryption failed]":
        key_hash = _hash_key(decrypted_key)
        collision_msg = await _check_hash_collision(key_hash, user_id, credential_id)
        if collision_msg:
            result["is_compromised"] = True
            result["sources_checked"].append("cross_user_hash_check")
            result["details"] += f"; {collision_msg}" if result["details"] != "No issues found" else collision_msg
    else:
        result["sources_checked"].append("cross_user_hash_check")

    now = datetime.now(timezone.utc)

    # Build recommendation
    recommendation = ""
    if result["is_compromised"]:
        recommendation = "This credential may be compromised. Rotate it immediately and review access logs."
    else:
        recommendation = "No issues detected. Continue monitoring regularly."

    # Store result in db
    check_doc = {
        "id": str(uuid.uuid4()),
        "credential_id": credential_id,
        "user_id": user_id,
        "is_compromised": result["is_compromised"],
        "source": ", ".join(result["sources_checked"]),
        "check_timestamp": now,
        "details": result["details"],
    }
    await db.breach_checks.insert_one(check_doc)

    return BreachCheckResponse(
        credential_id=credential_id,
        api_name=credential["api_name"],
        is_compromised=result["is_compromised"],
        sources_checked=result["sources_checked"],
        last_checked=now,
        recommendation=recommendation,
    )


@router.post("/breach-check/{credential_id}", response_model=BreachCheckResponse)
async def check_credential_breach(
    credential_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Check a credential against known breach patterns."""
    return await _run_breach_check(credential_id, current_user["id"])


@router.get("/breach-check/results", response_model=list[dict])
async def get_breach_check_results(
    current_user: dict = Depends(get_current_user),
):
    """Get all breach check results for the authenticated user."""
    results = await db.breach_checks.find(
        {"user_id": current_user["id"]}
    ).to_list(1000)

    for r in results:
        r.pop("_id", None)

    return results


@router.post("/breach-check/scan-all", response_model=dict)
async def scan_all_credentials(
    current_user: dict = Depends(get_current_user),
):
    """Run breach check on all user's credentials and return summary."""
    credentials = await db.credentials.find(
        {"user_id": current_user["id"]}
    ).to_list(1000)

    if not credentials:
        return {
            "total_checked": 0,
            "compromised_count": 0,
            "clean_count": 0,
            "results": [],
        }

    results = []
    compromised_count = 0
    for cred in credentials:
        check_result = await _run_breach_check(cred["id"], current_user["id"])
        if check_result.is_compromised:
            compromised_count += 1
        results.append(check_result.model_dump())

    return {
        "total_checked": len(results),
        "compromised_count": compromised_count,
        "clean_count": len(results) - compromised_count,
        "results": results,
    }


@router.get("/breach-check/summary", response_model=dict)
async def get_breach_check_summary(
    current_user: dict = Depends(get_current_user),
):
    """Get breach check summary for the authenticated user."""
    checks = await db.breach_checks.find(
        {"user_id": current_user["id"]}
    ).sort("check_timestamp", -1).to_list(1000)

    total_checked = len(checks)
    compromised_count = sum(1 for c in checks if c.get("is_compromised", False))
    last_scan = checks[0]["check_timestamp"] if checks else None

    return {
        "total_checked": total_checked,
        "compromised_count": compromised_count,
        "clean_count": total_checked - compromised_count,
        "last_scan_date": last_scan,
    }
