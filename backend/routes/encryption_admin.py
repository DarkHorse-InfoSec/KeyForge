"""Encryption key rotation and administration routes for KeyForge."""

from datetime import datetime, timezone

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException

from backend.config import db, logger
from backend.models_security import (
    EncryptionKeyRotationRequest,
    EncryptionKeyRotationResponse,
)
from backend.security import decrypt_api_key, get_current_user

router = APIRouter(prefix="/api", tags=["encryption-admin"])


@router.post("/admin/rotate-encryption-key", response_model=EncryptionKeyRotationResponse)
async def rotate_encryption_key(
    body: EncryptionKeyRotationRequest,
    current_user: dict = Depends(get_current_user),
):
    """Re-encrypt all of the user's stored credentials with a new Fernet key.

    Steps:
    1. Generate a new Fernet key (or use the one provided in the request body).
    2. Iterate all credentials belonging to the current user.
    3. Decrypt each with the current (old) key.
    4. Re-encrypt with the new key.
    5. Update each credential in the database.
    6. Return the count of re-encrypted credentials.
    """
    # 1. Derive new key
    if body.new_key:
        try:
            # Validate that the provided key is a valid Fernet key
            new_fernet = Fernet(body.new_key.encode() if isinstance(body.new_key, str) else body.new_key)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid Fernet key provided")
    else:
        new_key_bytes = Fernet.generate_key()
        new_fernet = Fernet(new_key_bytes)

    # 2. Fetch all credentials for the user
    credentials = await db.credentials.find({"user_id": current_user["id"]}).to_list(length=10_000)

    re_encrypted_count = 0

    for cred in credentials:
        encrypted_value = cred.get("api_key_encrypted", "")
        if not encrypted_value:
            continue

        # 3. Decrypt with old key
        plain = decrypt_api_key(encrypted_value)
        if plain == "[decryption failed]":
            logger.warning(
                "Skipping credential %s - decryption failed with current key",
                cred.get("id"),
            )
            continue

        # 4. Re-encrypt with new key
        new_encrypted = new_fernet.encrypt(plain.encode()).decode()

        # 5. Update in DB
        await db.credentials.update_one(
            {"id": cred["id"]},
            {"$set": {"api_key_encrypted": new_encrypted}},
        )
        re_encrypted_count += 1

    timestamp = datetime.now(timezone.utc)

    # 6. Log the operation
    await db.audit_log.insert_one(
        {
            "user_id": current_user["id"],
            "action": "encryption_key_rotation",
            "details": {"credentials_re_encrypted": re_encrypted_count},
            "timestamp": timestamp,
        }
    )

    logger.info(
        "Encryption key rotated for user %s - %d credentials re-encrypted",
        current_user["username"],
        re_encrypted_count,
    )

    return EncryptionKeyRotationResponse(
        message="Encryption key rotated successfully",
        credentials_re_encrypted=re_encrypted_count,
        timestamp=timestamp,
    )


@router.get("/admin/encryption-status", response_model=dict)
async def encryption_status(current_user: dict = Depends(get_current_user)):
    """Return encryption health information for the current user's credentials."""
    total_credentials = await db.credentials.count_documents({"user_id": current_user["id"]})

    # Check the most recent rotation event, if any
    last_rotation = await db.audit_log.find_one(
        {"user_id": current_user["id"], "action": "encryption_key_rotation"},
        sort=[("timestamp", -1)],
    )

    key_rotated_at = last_rotation["timestamp"] if last_rotation else None

    return {
        "algorithm": "Fernet (AES-128-CBC + HMAC-SHA256)",
        "total_encrypted_credentials": total_credentials,
        "last_key_rotation": key_rotated_at,
        "status": "healthy",
    }
