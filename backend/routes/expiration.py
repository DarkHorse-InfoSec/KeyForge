"""Credential expiration alert routes for KeyForge."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime, timezone

try:
    from ..config import db
    from ..security import get_current_user
    from ..models_lifecycle import (
        CredentialExpiration,
        CredentialExpirationCreate,
        CredentialExpirationResponse,
    )
except ImportError:
    from backend.config import db
    from backend.security import get_current_user
    from backend.models_lifecycle import (
        CredentialExpiration,
        CredentialExpirationCreate,
        CredentialExpirationResponse,
    )

router = APIRouter(prefix="/api", tags=["expiration"])


def _compute_expiration_fields(exp_doc: dict, api_name: str = "") -> CredentialExpirationResponse:
    """Build a response with computed days_until_expiry and is_expired."""
    expires_at = exp_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    delta = expires_at - now
    days_until = delta.days

    return CredentialExpirationResponse(
        id=exp_doc["id"],
        credential_id=exp_doc["credential_id"],
        api_name=api_name,
        expires_at=expires_at,
        days_until_expiry=max(days_until, 0),
        alert_days_before=exp_doc.get("alert_days_before", 7),
        is_expired=days_until < 0,
        alert_sent=exp_doc.get("alert_sent", False),
    )


@router.post("/expirations", response_model=CredentialExpirationResponse)
async def set_expiration(
    data: CredentialExpirationCreate,
    current_user: dict = Depends(get_current_user),
):
    """Set expiration date for a credential."""
    # Verify credential belongs to user
    credential = await db.credentials.find_one({
        "id": data.credential_id,
        "user_id": current_user["id"],
    })
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    exp = CredentialExpiration(
        credential_id=data.credential_id,
        user_id=current_user["id"],
        expires_at=data.expires_at,
        alert_days_before=data.alert_days_before,
    )

    exp_doc = exp.model_dump()
    await db.expirations.insert_one(exp_doc)

    return _compute_expiration_fields(exp_doc, api_name=credential.get("api_name", ""))


@router.get("/expirations", response_model=List[CredentialExpirationResponse])
async def list_expirations(
    current_user: dict = Depends(get_current_user),
):
    """List all expiration entries for the authenticated user."""
    expirations = await db.expirations.find(
        {"user_id": current_user["id"]}
    ).to_list(1000)

    results = []
    for exp_doc in expirations:
        # Look up api_name from the credential
        credential = await db.credentials.find_one({"id": exp_doc["credential_id"]})
        api_name = credential.get("api_name", "") if credential else ""
        results.append(_compute_expiration_fields(exp_doc, api_name=api_name))

    return results


@router.get("/expirations/alerts", response_model=List[CredentialExpirationResponse])
async def get_expiration_alerts(
    current_user: dict = Depends(get_current_user),
):
    """Get credentials expiring within their alert window."""
    expirations = await db.expirations.find(
        {"user_id": current_user["id"]}
    ).to_list(1000)

    alerts = []
    for exp_doc in expirations:
        credential = await db.credentials.find_one({"id": exp_doc["credential_id"]})
        api_name = credential.get("api_name", "") if credential else ""
        response = _compute_expiration_fields(exp_doc, api_name=api_name)
        # Include if expiring within alert window or already expired
        if response.days_until_expiry <= response.alert_days_before or response.is_expired:
            alerts.append(response)

    return alerts


@router.put("/expirations/{expiration_id}", response_model=CredentialExpirationResponse)
async def update_expiration(
    expiration_id: str,
    data: CredentialExpirationCreate,
    current_user: dict = Depends(get_current_user),
):
    """Update expiration date or alert settings."""
    exp_doc = await db.expirations.find_one({
        "id": expiration_id,
        "user_id": current_user["id"],
    })
    if not exp_doc:
        raise HTTPException(status_code=404, detail="Expiration entry not found")

    update_data = {
        "expires_at": data.expires_at,
        "alert_days_before": data.alert_days_before,
        "alert_sent": False,
    }

    await db.expirations.update_one(
        {"id": expiration_id, "user_id": current_user["id"]},
        {"$set": update_data},
    )

    updated = await db.expirations.find_one({"id": expiration_id})
    credential = await db.credentials.find_one({"id": updated["credential_id"]})
    api_name = credential.get("api_name", "") if credential else ""

    return _compute_expiration_fields(updated, api_name=api_name)


@router.delete("/expirations/{expiration_id}", response_model=dict)
async def delete_expiration(
    expiration_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Remove expiration tracking."""
    result = await db.expirations.delete_one({
        "id": expiration_id,
        "user_id": current_user["id"],
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Expiration entry not found")
    return {"message": "Expiration tracking removed successfully"}


@router.get("/expirations/summary", response_model=dict)
async def get_expiration_summary(
    current_user: dict = Depends(get_current_user),
):
    """Summary: total tracked, expired count, expiring soon count."""
    expirations = await db.expirations.find(
        {"user_id": current_user["id"]}
    ).to_list(1000)

    total = len(expirations)
    expired_count = 0
    expiring_soon_count = 0

    now = datetime.now(timezone.utc)
    for exp_doc in expirations:
        expires_at = exp_doc["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        delta = expires_at - now
        days_until = delta.days
        alert_days = exp_doc.get("alert_days_before", 7)

        if days_until < 0:
            expired_count += 1
        elif days_until <= alert_days:
            expiring_soon_count += 1

    return {
        "total_tracked": total,
        "expired_count": expired_count,
        "expiring_soon_count": expiring_soon_count,
    }
