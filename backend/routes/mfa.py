"""MFA/2FA routes for KeyForge using TOTP (Time-based One-Time Passwords)."""

import hashlib
import secrets

import pyotp
from fastapi import APIRouter, Depends, HTTPException

from backend.config import db, logger
from backend.models_security import MFASetup, MFAStatusResponse, MFAVerify
from backend.security import get_current_user

router = APIRouter(prefix="/api", tags=["mfa"])


def _hash_secret(value: str) -> str:
    """Return a SHA-256 hex digest of the given value."""
    return hashlib.sha256(value.encode()).hexdigest()


def _generate_backup_codes(count: int = 8) -> list[str]:
    """Generate *count* random 8-character hex backup codes."""
    return [secrets.token_hex(4) for _ in range(count)]


@router.post("/mfa/setup", response_model=MFASetup)
async def mfa_setup(current_user: dict = Depends(get_current_user)):
    """Generate a TOTP secret, provisioning URI, and backup codes for MFA enrolment."""
    # Check if MFA is already enabled
    if current_user.get("mfa_secret"):
        raise HTTPException(status_code=400, detail="MFA is already enabled")

    secret = pyotp.random_base32()
    provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user["username"],
        issuer_name="KeyForge",
    )

    backup_codes = _generate_backup_codes(8)
    hashed_backup_codes = [_hash_secret(code) for code in backup_codes]

    # Store hashed secret and backup codes in the user document
    await db.users.update_one(
        {"username": current_user["username"]},
        {
            "$set": {
                "mfa_secret": _hash_secret(secret),
                "mfa_secret_plain": secret,  # Needed to verify codes later
                "mfa_backup_codes": hashed_backup_codes,
                "mfa_enabled_at": None,  # Not yet verified/enabled
            }
        },
    )

    logger.info("MFA setup initiated for user %s", current_user["username"])

    return MFASetup(
        secret=secret,
        provisioning_uri=provisioning_uri,
        backup_codes=backup_codes,
    )


@router.post("/mfa/verify", response_model=dict)
async def mfa_verify(body: MFAVerify, current_user: dict = Depends(get_current_user)):
    """Verify a TOTP code against the stored secret. Also used to finalise MFA setup."""
    secret = current_user.get("mfa_secret_plain")
    if not secret:
        raise HTTPException(status_code=400, detail="MFA is not set up")

    totp = pyotp.TOTP(secret)

    if totp.verify(body.code):
        # If MFA was just set up (mfa_enabled_at is None), mark it as enabled
        from datetime import datetime, timezone

        if not current_user.get("mfa_enabled_at"):
            await db.users.update_one(
                {"username": current_user["username"]},
                {"$set": {"mfa_enabled_at": datetime.now(timezone.utc)}},
            )

        logger.info("MFA code verified for user %s", current_user["username"])
        return {"verified": True}

    # Check backup codes
    code_hash = _hash_secret(body.code)
    backup_codes = current_user.get("mfa_backup_codes", [])
    if code_hash in backup_codes:
        # Remove used backup code
        backup_codes.remove(code_hash)
        await db.users.update_one(
            {"username": current_user["username"]},
            {"$set": {"mfa_backup_codes": backup_codes}},
        )
        logger.info("MFA backup code used by user %s", current_user["username"])
        return {"verified": True, "backup_code_used": True}

    raise HTTPException(status_code=400, detail="Invalid TOTP code")


@router.post("/mfa/disable", response_model=dict)
async def mfa_disable(body: MFAVerify, current_user: dict = Depends(get_current_user)):
    """Disable MFA for the current user. Requires a valid TOTP code to confirm."""
    secret = current_user.get("mfa_secret_plain")
    if not secret:
        raise HTTPException(status_code=400, detail="MFA is not enabled")

    totp = pyotp.TOTP(secret)
    if not totp.verify(body.code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    await db.users.update_one(
        {"username": current_user["username"]},
        {
            "$unset": {
                "mfa_secret": "",
                "mfa_secret_plain": "",
                "mfa_backup_codes": "",
                "mfa_enabled_at": "",
            }
        },
    )

    logger.info("MFA disabled for user %s", current_user["username"])
    return {"message": "MFA has been disabled"}


@router.get("/mfa/status", response_model=MFAStatusResponse)
async def mfa_status(current_user: dict = Depends(get_current_user)):
    """Check whether MFA is enabled for the current user."""
    enabled = bool(current_user.get("mfa_secret"))
    created_at = current_user.get("mfa_enabled_at")

    return MFAStatusResponse(enabled=enabled, created_at=created_at)
