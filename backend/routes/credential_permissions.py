"""Per-credential RBAC routes for KeyForge."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime, timezone

try:
    from ..config import db
    from ..security import get_current_user
    from ..models_lifecycle import (
        CredentialPermission,
        CredentialPermissionCreate,
        CredentialPermissionResponse,
    )
except ImportError:
    from backend.config import db
    from backend.security import get_current_user
    from backend.models_lifecycle import (
        CredentialPermission,
        CredentialPermissionCreate,
        CredentialPermissionResponse,
    )

router = APIRouter(prefix="/api", tags=["credential-permissions"])

VALID_PERMISSIONS = {"read", "use", "manage", "admin"}


@router.post("/credential-permissions", response_model=CredentialPermissionResponse)
async def grant_permission(
    data: CredentialPermissionCreate,
    current_user: dict = Depends(get_current_user),
):
    """Grant permission on a credential to another user (by username). Only credential owner can grant."""
    # Verify credential belongs to current user (owner)
    credential = await db.credentials.find_one({
        "id": data.credential_id,
        "user_id": current_user["id"],
    })
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found or you are not the owner")

    # Validate permission level
    if data.permission not in VALID_PERMISSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Permission must be one of: {', '.join(sorted(VALID_PERMISSIONS))}",
        )

    # Look up target user by username
    target_user = await db.users.find_one({"username": data.username})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_user_id = str(target_user["_id"]) if "_id" in target_user else target_user.get("id", "")

    # Prevent granting permission to yourself
    if target_user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot grant permission to yourself")

    # Check if permission already exists
    existing = await db.credential_permissions.find_one({
        "credential_id": data.credential_id,
        "user_id": target_user_id,
    })
    if existing:
        raise HTTPException(status_code=400, detail="Permission already exists for this user on this credential")

    perm = CredentialPermission(
        credential_id=data.credential_id,
        user_id=target_user_id,
        granted_by=current_user["id"],
        permission=data.permission,
    )

    perm_doc = perm.model_dump()
    await db.credential_permissions.insert_one(perm_doc)

    return CredentialPermissionResponse(
        id=perm_doc["id"],
        credential_id=perm_doc["credential_id"],
        api_name=credential.get("api_name", ""),
        user_id=target_user_id,
        username=data.username,
        permission=perm_doc["permission"],
        granted_by=perm_doc["granted_by"],
        created_at=perm_doc["created_at"],
    )


@router.get("/credential-permissions/{credential_id}", response_model=List[CredentialPermissionResponse])
async def list_permissions(
    credential_id: str,
    current_user: dict = Depends(get_current_user),
):
    """List all permissions for a credential. Only owner can view."""
    # Verify ownership
    credential = await db.credentials.find_one({
        "id": credential_id,
        "user_id": current_user["id"],
    })
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found or you are not the owner")

    permissions = await db.credential_permissions.find(
        {"credential_id": credential_id}
    ).to_list(1000)

    results = []
    for perm_doc in permissions:
        # Look up username
        user = await db.users.find_one({"_id": perm_doc["user_id"]})
        if not user:
            # Try matching by string id field
            user = await db.users.find_one({"id": perm_doc["user_id"]})
        username = user.get("username", "") if user else ""

        results.append(CredentialPermissionResponse(
            id=perm_doc["id"],
            credential_id=perm_doc["credential_id"],
            api_name=credential.get("api_name", ""),
            user_id=perm_doc["user_id"],
            username=username,
            permission=perm_doc["permission"],
            granted_by=perm_doc["granted_by"],
            created_at=perm_doc["created_at"],
        ))

    return results


@router.delete("/credential-permissions/{permission_id}", response_model=dict)
async def revoke_permission(
    permission_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Revoke a permission. Only owner can revoke."""
    perm_doc = await db.credential_permissions.find_one({"id": permission_id})
    if not perm_doc:
        raise HTTPException(status_code=404, detail="Permission not found")

    # Only the owner (granted_by) can revoke
    if perm_doc["granted_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only the credential owner can revoke permissions")

    await db.credential_permissions.delete_one({"id": permission_id})
    return {"message": "Permission revoked successfully"}


@router.get("/credential-permissions/shared-with-me", response_model=List[CredentialPermissionResponse])
async def shared_with_me(
    current_user: dict = Depends(get_current_user),
):
    """List credentials shared with the current user, with permission level."""
    permissions = await db.credential_permissions.find(
        {"user_id": current_user["id"]}
    ).to_list(1000)

    results = []
    for perm_doc in permissions:
        credential = await db.credentials.find_one({"id": perm_doc["credential_id"]})
        api_name = credential.get("api_name", "") if credential else ""

        # Look up who granted
        granter = await db.users.find_one({"id": perm_doc["granted_by"]})
        if not granter:
            from bson import ObjectId
            try:
                granter = await db.users.find_one({"_id": ObjectId(perm_doc["granted_by"])})
            except Exception:
                granter = None

        results.append(CredentialPermissionResponse(
            id=perm_doc["id"],
            credential_id=perm_doc["credential_id"],
            api_name=api_name,
            user_id=perm_doc["user_id"],
            username=current_user.get("username", ""),
            permission=perm_doc["permission"],
            granted_by=perm_doc["granted_by"],
            created_at=perm_doc["created_at"],
        ))

    return results


@router.get("/credential-permissions/my-shares", response_model=List[CredentialPermissionResponse])
async def my_shares(
    current_user: dict = Depends(get_current_user),
):
    """List all permissions the current user has granted to others."""
    permissions = await db.credential_permissions.find(
        {"granted_by": current_user["id"]}
    ).to_list(1000)

    results = []
    for perm_doc in permissions:
        credential = await db.credentials.find_one({"id": perm_doc["credential_id"]})
        api_name = credential.get("api_name", "") if credential else ""

        # Look up the target user's username
        user = await db.users.find_one({"_id": perm_doc["user_id"]})
        if not user:
            user = await db.users.find_one({"id": perm_doc["user_id"]})
        username = user.get("username", "") if user else ""

        results.append(CredentialPermissionResponse(
            id=perm_doc["id"],
            credential_id=perm_doc["credential_id"],
            api_name=api_name,
            user_id=perm_doc["user_id"],
            username=username,
            permission=perm_doc["permission"],
            granted_by=perm_doc["granted_by"],
            created_at=perm_doc["created_at"],
        ))

    return results
