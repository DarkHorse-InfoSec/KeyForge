"""Auto-rotation configuration routes for KeyForge."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

try:
    from ..config import db
    from ..models_lifecycle import AutoRotationConfig, AutoRotationConfigCreate
    from ..security import decrypt_api_key, get_current_user
except ImportError:
    from backend.config import db
    from backend.models_lifecycle import AutoRotationConfig, AutoRotationConfigCreate
    from backend.security import decrypt_api_key, get_current_user

router = APIRouter(prefix="/api", tags=["auto-rotation"])

SUPPORTED_PROVIDERS = {
    "aws": {
        "name": "AWS",
        "description": "Amazon Web Services IAM access keys",
        "default_interval_days": 90,
        "min_interval_days": 1,
        "max_interval_days": 365,
    },
    "github": {
        "name": "GitHub",
        "description": "GitHub personal access tokens and app tokens",
        "default_interval_days": 90,
        "min_interval_days": 1,
        "max_interval_days": 365,
    },
    "stripe": {
        "name": "Stripe",
        "description": "Stripe API keys (secret and publishable)",
        "default_interval_days": 90,
        "min_interval_days": 30,
        "max_interval_days": 365,
    },
}


class AutoRotationConfigUpdate(BaseModel):
    rotation_interval_days: Optional[int] = None
    enabled: Optional[bool] = None


@router.post("/auto-rotation", response_model=dict)
async def configure_auto_rotation(
    data: AutoRotationConfigCreate,
    current_user: dict = Depends(get_current_user),
):
    """Configure auto-rotation for a credential."""
    # Verify credential belongs to user
    credential = await db.credentials.find_one(
        {
            "id": data.credential_id,
            "user_id": current_user["id"],
        }
    )
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    # Check provider is supported
    provider = credential.get("api_name", "").lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Auto-rotation is not supported for provider '{provider}'. "
            f"Supported providers: {', '.join(SUPPORTED_PROVIDERS.keys())}",
        )

    # Check if config already exists
    existing = await db.auto_rotation_configs.find_one(
        {
            "credential_id": data.credential_id,
            "user_id": current_user["id"],
        }
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Auto-rotation config already exists for this credential",
        )

    now = datetime.now(timezone.utc)
    next_rotation = now + timedelta(days=data.rotation_interval_days)

    config = AutoRotationConfig(
        credential_id=data.credential_id,
        user_id=current_user["id"],
        provider=provider,
        rotation_interval_days=data.rotation_interval_days,
        last_rotated=None,
        next_rotation=next_rotation,
        enabled=data.enabled,
    )

    config_doc = config.model_dump()
    await db.auto_rotation_configs.insert_one(config_doc)

    return {
        "id": config_doc["id"],
        "credential_id": config_doc["credential_id"],
        "provider": config_doc["provider"],
        "rotation_interval_days": config_doc["rotation_interval_days"],
        "last_rotated": config_doc["last_rotated"],
        "next_rotation": config_doc["next_rotation"],
        "enabled": config_doc["enabled"],
        "created_at": config_doc["created_at"],
    }


@router.get("/auto-rotation", response_model=list[dict])
async def list_auto_rotation_configs(
    current_user: dict = Depends(get_current_user),
):
    """List all auto-rotation configs for the authenticated user."""
    configs = await db.auto_rotation_configs.find({"user_id": current_user["id"]}).to_list(1000)

    results = []
    for config_doc in configs:
        credential = await db.credentials.find_one({"id": config_doc["credential_id"]})
        api_name = credential.get("api_name", "") if credential else ""
        results.append(
            {
                "id": config_doc["id"],
                "credential_id": config_doc["credential_id"],
                "api_name": api_name,
                "provider": config_doc["provider"],
                "rotation_interval_days": config_doc["rotation_interval_days"],
                "last_rotated": config_doc.get("last_rotated"),
                "next_rotation": config_doc.get("next_rotation"),
                "enabled": config_doc.get("enabled", True),
                "created_at": config_doc["created_at"],
            }
        )

    return results


@router.put("/auto-rotation/{config_id}", response_model=dict)
async def update_auto_rotation_config(
    config_id: str,
    data: AutoRotationConfigUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update auto-rotation config (interval, enabled)."""
    config_doc = await db.auto_rotation_configs.find_one(
        {
            "id": config_id,
            "user_id": current_user["id"],
        }
    )
    if not config_doc:
        raise HTTPException(status_code=404, detail="Auto-rotation config not found")

    update_data = {}
    if data.rotation_interval_days is not None:
        update_data["rotation_interval_days"] = data.rotation_interval_days
        # Recalculate next_rotation based on last_rotated or now
        base_time = config_doc.get("last_rotated") or datetime.now(timezone.utc)
        if isinstance(base_time, str):
            base_time = datetime.fromisoformat(base_time)
        update_data["next_rotation"] = base_time + timedelta(days=data.rotation_interval_days)

    if data.enabled is not None:
        update_data["enabled"] = data.enabled

    if update_data:
        await db.auto_rotation_configs.update_one(
            {"id": config_id, "user_id": current_user["id"]},
            {"$set": update_data},
        )

    updated = await db.auto_rotation_configs.find_one({"id": config_id})
    return {
        "id": updated["id"],
        "credential_id": updated["credential_id"],
        "provider": updated["provider"],
        "rotation_interval_days": updated["rotation_interval_days"],
        "last_rotated": updated.get("last_rotated"),
        "next_rotation": updated.get("next_rotation"),
        "enabled": updated.get("enabled", True),
        "created_at": updated["created_at"],
    }


@router.delete("/auto-rotation/{config_id}", response_model=dict)
async def delete_auto_rotation_config(
    config_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Disable and remove auto-rotation config."""
    result = await db.auto_rotation_configs.delete_one(
        {
            "id": config_id,
            "user_id": current_user["id"],
        }
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Auto-rotation config not found")
    return {"message": "Auto-rotation config removed successfully"}


@router.post("/auto-rotation/{config_id}/trigger", response_model=dict)
async def trigger_rotation(
    config_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Manually trigger rotation for a config (stub implementation)."""
    config_doc = await db.auto_rotation_configs.find_one(
        {
            "id": config_id,
            "user_id": current_user["id"],
        }
    )
    if not config_doc:
        raise HTTPException(status_code=404, detail="Auto-rotation config not found")

    if not config_doc.get("enabled", True):
        raise HTTPException(status_code=400, detail="Auto-rotation is disabled for this config")

    # Look up the credential to validate current key
    credential = await db.credentials.find_one({"id": config_doc["credential_id"]})
    if not credential:
        raise HTTPException(status_code=404, detail="Associated credential not found")

    # Validate the current key exists and can be decrypted
    current_key = decrypt_api_key(credential.get("api_key", ""))
    key_valid = current_key != "[decryption failed]"

    provider = config_doc["provider"]
    provider_info = SUPPORTED_PROVIDERS.get(provider, {})

    # Stub: describe what would happen
    now = datetime.now(timezone.utc)
    next_rotation = now + timedelta(days=config_doc["rotation_interval_days"])

    # Update last_rotated and next_rotation timestamps
    await db.auto_rotation_configs.update_one(
        {"id": config_id},
        {
            "$set": {
                "last_rotated": now,
                "next_rotation": next_rotation,
            }
        },
    )

    return {
        "config_id": config_id,
        "provider": provider,
        "credential_id": config_doc["credential_id"],
        "current_key_valid": key_valid,
        "status": "simulated",
        "message": (
            f"Auto-rotation triggered for {provider_info.get('name', provider)}. "
            f"In production, this would call the {provider_info.get('name', provider)} API to "
            f"generate a new key, encrypt it, store a new version, and update the credential. "
            f"Next rotation scheduled for {next_rotation.isoformat()}."
        ),
        "last_rotated": now,
        "next_rotation": next_rotation,
    }


@router.get("/auto-rotation/supported-providers", response_model=dict)
async def get_supported_providers(current_user: dict = Depends(get_current_user)):
    """Return list of providers that support auto-rotation with details."""
    return {"providers": [{"key": key, **details} for key, details in SUPPORTED_PROVIDERS.items()]}
