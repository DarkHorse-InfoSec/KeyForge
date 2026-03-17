"""API routes for encrypted backup and disaster recovery."""

import base64

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from backend.backup.manager import BackupManager
from backend.config import db
from backend.models_backup import (
    BackupCreate,
    BackupListResponse,
    BackupMetadata,
    BackupRestore,
    BackupSchedule,
    BackupVerification,
)
from backend.security import get_current_user

router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.post("/create", response_model=BackupMetadata)
async def create_backup(body: BackupCreate, current_user: dict = Depends(get_current_user)):
    """Create a new encrypted backup of the specified (or all) collections."""
    try:
        result = await BackupManager.create_backup(
            db,
            collections=body.collections,
            description=body.description,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/list", response_model=BackupListResponse)
async def list_backups(current_user: dict = Depends(get_current_user)):
    """List all backups with metadata."""
    backups = await BackupManager.list_backups(db)
    return BackupListResponse(backups=backups, total=len(backups))


@router.post("/restore/{backup_id}", response_model=dict)
async def restore_backup(backup_id: str, body: BackupRestore, current_user: dict = Depends(get_current_user)):
    """Restore collections from an encrypted backup."""
    # Fetch the encrypted blob
    blob_doc = await db["backup_data"].find_one({"backup_id": backup_id})
    if not blob_doc:
        raise HTTPException(status_code=404, detail="Backup data not found")

    backup_bytes = base64.b64decode(blob_doc["data"])
    try:
        result = await BackupManager.restore_backup(
            db,
            backup_data=backup_bytes,
            encryption_key=body.encryption_key,
            target_collections=body.target_collections,
            mode=body.mode,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/verify/{backup_id}", response_model=BackupVerification)
async def verify_backup(backup_id: str, current_user: dict = Depends(get_current_user)):
    """Verify backup integrity without restoring."""
    meta = await db["backups"].find_one({"backup_id": backup_id})
    if not meta:
        raise HTTPException(status_code=404, detail="Backup not found")

    blob_doc = await db["backup_data"].find_one({"backup_id": backup_id})
    if not blob_doc:
        raise HTTPException(status_code=404, detail="Backup data not found")

    encryption_key = meta.get("encryption_key")
    if not encryption_key:
        raise HTTPException(
            status_code=400,
            detail="No encryption key stored for this backup",
        )

    backup_bytes = base64.b64decode(blob_doc["data"])
    result = await BackupManager.verify_backup(backup_bytes, encryption_key)

    # Cross-check the stored checksum
    stored_checksum = meta.get("checksum")
    if stored_checksum and result.get("checksum"):
        result["checksum_match"] = stored_checksum == result["checksum"]

    result["backup_id"] = backup_id
    return result


@router.delete("/{backup_id}", response_model=dict)
async def delete_backup(backup_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a backup and its data."""
    deleted = await BackupManager.delete_backup(db, backup_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Backup not found")
    return {"deleted": True, "backup_id": backup_id}


@router.get("/download/{backup_id}")
async def download_backup(backup_id: str, current_user: dict = Depends(get_current_user)):
    """Download the raw encrypted backup file."""
    blob_doc = await db["backup_data"].find_one({"backup_id": backup_id})
    if not blob_doc:
        raise HTTPException(status_code=404, detail="Backup data not found")

    raw = base64.b64decode(blob_doc["data"])
    return Response(
        content=raw,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="backup-{backup_id}.enc.gz"'},
    )


@router.post("/schedule", response_model=dict)
async def set_schedule(body: BackupSchedule, current_user: dict = Depends(get_current_user)):
    """Configure the automated backup schedule."""
    result = await BackupManager.schedule_backup(
        db,
        cron_expression=body.cron_expression,
        collections=body.collections,
        enabled=body.enabled,
        retention_days=body.retention_days,
        description=body.description,
    )
    return result


@router.get("/schedule", response_model=dict)
async def get_schedule(current_user: dict = Depends(get_current_user)):
    """Get the current backup schedule."""
    schedule = await BackupManager.get_schedule(db)
    if not schedule:
        return {"message": "No backup schedule configured", "schedule": None}
    return {"schedule": schedule}
