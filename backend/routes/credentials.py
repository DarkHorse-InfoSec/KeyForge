"""Credential management routes for KeyForge."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
from datetime import datetime, timezone
import uuid

try:
    from ..config import db
    from ..models import CredentialCreate, CredentialUpdate, CredentialResponse
    from ..security import get_current_user, encrypt_api_key, decrypt_api_key
    from ..validators import validate_credential
except ImportError:
    from backend.config import db
    from backend.models import CredentialCreate, CredentialUpdate, CredentialResponse
    from backend.security import get_current_user, encrypt_api_key, decrypt_api_key
    from backend.validators import validate_credential

router = APIRouter(prefix="/api", tags=["credentials"])


def _validate(api_name: str, api_key: str) -> Dict:
    """Validate a credential using real format checks and live API calls."""
    return validate_credential(api_name, api_key)


def make_api_key_preview(api_key: str) -> str:
    """Return a masked preview of an API key showing only the last 4 characters."""
    if len(api_key) <= 4:
        return "****"
    return "****" + api_key[-4:]


def _preview_from_encrypted(encrypted_key: str) -> str:
    """Decrypt an API key and return a masked preview."""
    decrypted = decrypt_api_key(encrypted_key)
    if decrypted == "[decryption failed]":
        return "****"
    return make_api_key_preview(decrypted)


@router.post("/credentials", response_model=CredentialResponse)
async def create_credential(
    credential: CredentialCreate,
    current_user: dict = Depends(get_current_user),
):
    """Add a new API credential for the authenticated user."""
    # Encrypt the API key before storing
    encrypted_key = encrypt_api_key(credential.api_key)
    preview = make_api_key_preview(credential.api_key)

    # Mock validate the credential
    validation_result = _validate(credential.api_name, credential.api_key)

    cred_doc = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "api_name": credential.api_name,
        "api_key": encrypted_key,
        "status": validation_result["status"],
        "last_tested": datetime.now(timezone.utc),
        "environment": credential.environment,
        "created_at": datetime.now(timezone.utc),
    }

    await db.credentials.insert_one(cred_doc)

    return CredentialResponse(
        id=cred_doc["id"],
        api_name=cred_doc["api_name"],
        api_key_preview=preview,
        status=cred_doc["status"],
        last_tested=cred_doc["last_tested"],
        environment=cred_doc["environment"],
        created_at=cred_doc["created_at"],
    )


@router.get("/credentials", response_model=List[CredentialResponse])
async def get_credentials(
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """Get all credentials for the authenticated user with pagination."""
    credentials = await (
        db.credentials
        .find({"user_id": current_user["id"]})
        .skip(skip)
        .limit(limit)
        .to_list(limit)
    )

    return [
        CredentialResponse(
            id=cred["id"],
            api_name=cred["api_name"],
            api_key_preview=_preview_from_encrypted(cred.get("api_key", "")),
            status=cred.get("status", "unknown"),
            last_tested=cred.get("last_tested"),
            environment=cred.get("environment", "development"),
            created_at=cred.get("created_at"),
        )
        for cred in credentials
    ]


@router.get("/credentials/{credential_id}", response_model=CredentialResponse)
async def get_credential(
    credential_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get a specific credential owned by the authenticated user."""
    credential = await db.credentials.find_one({
        "id": credential_id,
        "user_id": current_user["id"],
    })
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    return CredentialResponse(
        id=credential["id"],
        api_name=credential["api_name"],
        api_key_preview=_preview_from_encrypted(credential.get("api_key", "")),
        status=credential.get("status", "unknown"),
        last_tested=credential.get("last_tested"),
        environment=credential.get("environment", "development"),
        created_at=credential.get("created_at"),
    )


@router.put("/credentials/{credential_id}", response_model=CredentialResponse)
async def update_credential(
    credential_id: str,
    update: CredentialUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update a credential owned by the authenticated user."""
    credential = await db.credentials.find_one({
        "id": credential_id,
        "user_id": current_user["id"],
    })
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    update_data = {k: v for k, v in update.dict().items() if v is not None}

    # If the API key is being updated, encrypt it and re-validate
    raw_key = None
    if "api_key" in update_data:
        raw_key = update_data["api_key"]
        update_data["api_key"] = encrypt_api_key(raw_key)
        validation_result = _validate(credential["api_name"], raw_key)
        update_data["status"] = validation_result["status"]
        update_data["last_tested"] = datetime.now(timezone.utc)

    if update_data:
        await db.credentials.update_one(
            {"id": credential_id, "user_id": current_user["id"]},
            {"$set": update_data},
        )

    updated = await db.credentials.find_one({"id": credential_id})

    if raw_key:
        preview = make_api_key_preview(raw_key)
    else:
        preview = _preview_from_encrypted(updated.get("api_key", ""))
    return CredentialResponse(
        id=updated["id"],
        api_name=updated["api_name"],
        api_key_preview=preview,
        status=updated.get("status", "unknown"),
        last_tested=updated.get("last_tested"),
        environment=updated.get("environment", "development"),
        created_at=updated.get("created_at"),
    )


@router.post("/credentials/{credential_id}/test", response_model=dict)
async def test_credential(
    credential_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Test a credential against its API (mock validation)."""
    credential = await db.credentials.find_one({
        "id": credential_id,
        "user_id": current_user["id"],
    })
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    # Decrypt the stored key to validate against the real API
    decrypted_key = decrypt_api_key(credential["api_key"])
    validation_result = _validate(credential["api_name"], decrypted_key)

    await db.credentials.update_one(
        {"id": credential_id, "user_id": current_user["id"]},
        {"$set": {
            "status": validation_result["status"],
            "last_tested": datetime.now(timezone.utc),
        }},
    )

    return {
        "credential_id": credential_id,
        "api_name": credential["api_name"],
        "test_result": validation_result,
    }


@router.delete("/credentials/{credential_id}", response_model=dict)
async def delete_credential(
    credential_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a credential owned by the authenticated user."""
    result = await db.credentials.delete_one({
        "id": credential_id,
        "user_id": current_user["id"],
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Credential not found")
    return {"message": "Credential deleted successfully"}
