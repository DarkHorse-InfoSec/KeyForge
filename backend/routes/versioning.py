"""Credential versioning routes for KeyForge."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

try:
    from ..config import db
    from ..models_lifecycle import CredentialVersion, CredentialVersionResponse
    from ..security import decrypt_api_key, encrypt_api_key, get_current_user
except ImportError:
    from backend.config import db
    from backend.models_lifecycle import CredentialVersion, CredentialVersionResponse
    from backend.security import decrypt_api_key, encrypt_api_key, get_current_user

router = APIRouter(prefix="/api", tags=["versioning"])


class VersionCreateRequest(BaseModel):
    api_key: str
    change_reason: str = ""


def _make_key_preview(encrypted_key: str) -> str:
    """Decrypt and return a masked preview of an API key."""
    decrypted = decrypt_api_key(encrypted_key)
    if decrypted == "[decryption failed]":
        return "****"
    if len(decrypted) <= 4:
        return "****"
    return "****" + decrypted[-4:]


@router.post("/credentials/{credential_id}/versions", response_model=CredentialVersionResponse)
async def create_version(
    credential_id: str,
    data: VersionCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new version of a credential's API key."""
    # Verify credential belongs to user
    credential = await db.credentials.find_one(
        {
            "id": credential_id,
            "user_id": current_user["id"],
        }
    )
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    # Get the current highest version number
    existing_versions = (
        await db.credential_versions.find({"credential_id": credential_id, "user_id": current_user["id"]})
        .sort("version_number", -1)
        .to_list(1)
    )

    next_version = 1
    if existing_versions:
        next_version = existing_versions[0]["version_number"] + 1

    # Mark all previous versions as not current
    await db.credential_versions.update_many(
        {"credential_id": credential_id, "user_id": current_user["id"]},
        {"$set": {"is_current": False}},
    )

    # Encrypt the new key
    encrypted_key = encrypt_api_key(data.api_key)

    # Create the new version
    version = CredentialVersion(
        credential_id=credential_id,
        user_id=current_user["id"],
        version_number=next_version,
        api_key_encrypted=encrypted_key,
        change_reason=data.change_reason,
        is_current=True,
    )

    version_doc = version.model_dump()
    await db.credential_versions.insert_one(version_doc)

    # Update the credential's api_key to the new version
    await db.credentials.update_one(
        {"id": credential_id, "user_id": current_user["id"]},
        {"$set": {"api_key": encrypted_key}},
    )

    return CredentialVersionResponse(
        id=version_doc["id"],
        credential_id=credential_id,
        version_number=version_doc["version_number"],
        api_key_preview=_make_key_preview(encrypted_key),
        change_reason=version_doc["change_reason"],
        created_at=version_doc["created_at"],
        is_current=True,
    )


@router.get(
    "/credentials/{credential_id}/versions",
    response_model=List[CredentialVersionResponse],
)
async def list_versions(
    credential_id: str,
    current_user: dict = Depends(get_current_user),
):
    """List all versions for a credential (masked key previews)."""
    # Verify credential belongs to user
    credential = await db.credentials.find_one(
        {
            "id": credential_id,
            "user_id": current_user["id"],
        }
    )
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    versions = (
        await db.credential_versions.find({"credential_id": credential_id, "user_id": current_user["id"]})
        .sort("version_number", -1)
        .to_list(1000)
    )

    return [
        CredentialVersionResponse(
            id=v["id"],
            credential_id=v["credential_id"],
            version_number=v["version_number"],
            api_key_preview=_make_key_preview(v["api_key_encrypted"]),
            change_reason=v.get("change_reason", ""),
            created_at=v["created_at"],
            is_current=v.get("is_current", False),
        )
        for v in versions
    ]


@router.post(
    "/credentials/{credential_id}/versions/{version_id}/rollback",
    response_model=CredentialVersionResponse,
)
async def rollback_version(
    credential_id: str,
    version_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Rollback to a previous version (copy its encrypted key to the credential, mark it current)."""
    # Verify credential belongs to user
    credential = await db.credentials.find_one(
        {
            "id": credential_id,
            "user_id": current_user["id"],
        }
    )
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    # Find the target version
    target_version = await db.credential_versions.find_one(
        {
            "id": version_id,
            "credential_id": credential_id,
            "user_id": current_user["id"],
        }
    )
    if not target_version:
        raise HTTPException(status_code=404, detail="Version not found")

    # Mark all versions as not current
    await db.credential_versions.update_many(
        {"credential_id": credential_id, "user_id": current_user["id"]},
        {"$set": {"is_current": False}},
    )

    # Mark the target version as current
    await db.credential_versions.update_one(
        {"id": version_id},
        {"$set": {"is_current": True}},
    )

    # Update the credential's api_key to the rolled-back version
    await db.credentials.update_one(
        {"id": credential_id, "user_id": current_user["id"]},
        {"$set": {"api_key": target_version["api_key_encrypted"]}},
    )

    return CredentialVersionResponse(
        id=target_version["id"],
        credential_id=credential_id,
        version_number=target_version["version_number"],
        api_key_preview=_make_key_preview(target_version["api_key_encrypted"]),
        change_reason=target_version.get("change_reason", ""),
        created_at=target_version["created_at"],
        is_current=True,
    )


@router.get(
    "/credentials/{credential_id}/versions/current",
    response_model=CredentialVersionResponse,
)
async def get_current_version(
    credential_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get the current version details for a credential."""
    # Verify credential belongs to user
    credential = await db.credentials.find_one(
        {
            "id": credential_id,
            "user_id": current_user["id"],
        }
    )
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    current_ver = await db.credential_versions.find_one(
        {
            "credential_id": credential_id,
            "user_id": current_user["id"],
            "is_current": True,
        }
    )
    if not current_ver:
        raise HTTPException(status_code=404, detail="No current version found")

    return CredentialVersionResponse(
        id=current_ver["id"],
        credential_id=credential_id,
        version_number=current_ver["version_number"],
        api_key_preview=_make_key_preview(current_ver["api_key_encrypted"]),
        change_reason=current_ver.get("change_reason", ""),
        created_at=current_ver["created_at"],
        is_current=True,
    )
