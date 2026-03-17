"""Credential lifecycle visualization routes for KeyForge."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid

try:
    from ..config import db, logger
    from ..security import get_current_user
    from ..models_analytics import LifecycleEvent, LifecycleTimelineResponse
except ImportError:
    from backend.config import db, logger
    from backend.security import get_current_user
    from backend.models_analytics import LifecycleEvent, LifecycleTimelineResponse

router = APIRouter(prefix="/api", tags=["lifecycle"])

VALID_EVENT_TYPES = [
    "created", "tested", "rotated", "shared", "expired",
    "revoked", "version_created", "permission_changed",
]


class RecordLifecycleEventRequest(BaseModel):
    credential_id: str
    event_type: str
    details: Optional[str] = ""


@router.post("/lifecycle/events")
async def record_lifecycle_event(
    body: RecordLifecycleEventRequest,
    current_user: dict = Depends(get_current_user),
):
    """Record a lifecycle event for a credential."""
    if body.event_type not in VALID_EVENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"event_type must be one of: {', '.join(VALID_EVENT_TYPES)}",
        )

    # Verify credential belongs to user
    credential = await db.credentials.find_one({
        "id": body.credential_id,
        "user_id": current_user["id"],
    })
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    event_doc = {
        "id": str(uuid.uuid4()),
        "credential_id": body.credential_id,
        "user_id": current_user["id"],
        "event_type": body.event_type,
        "details": body.details or "",
        "timestamp": datetime.now(timezone.utc),
    }
    await db.lifecycle_events.insert_one(event_doc)

    return {"message": "Lifecycle event recorded", "event_id": event_doc["id"]}


@router.get("/lifecycle/{credential_id}/timeline")
async def get_credential_timeline(
    credential_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get full timeline of events for a credential, sorted chronologically."""
    credential = await db.credentials.find_one({
        "id": credential_id,
        "user_id": current_user["id"],
    })
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    events = await db.lifecycle_events.find(
        {"credential_id": credential_id, "user_id": current_user["id"]}
    ).sort("timestamp", 1).to_list(1000)

    event_list = []
    for e in events:
        e.pop("_id", None)
        event_list.append(e)

    # Determine current status from most recent relevant event
    current_status = credential.get("status", "unknown")
    if events:
        last_event = events[-1]
        event_type = last_event.get("event_type", "")
        if event_type == "revoked":
            current_status = "revoked"
        elif event_type == "expired":
            current_status = "expired"
        elif event_type == "rotated":
            current_status = "active"

    return {
        "credential_id": credential_id,
        "api_name": credential["api_name"],
        "events": event_list,
        "created_at": credential.get("created_at"),
        "current_status": current_status,
    }


@router.get("/lifecycle/recent")
async def get_recent_lifecycle_events(
    current_user: dict = Depends(get_current_user),
):
    """Get recent lifecycle events across all user's credentials (last 50)."""
    events = await db.lifecycle_events.find(
        {"user_id": current_user["id"]}
    ).sort("timestamp", -1).limit(50).to_list(50)

    # Enrich with credential api_name
    cred_ids = list({e["credential_id"] for e in events})
    credentials = await db.credentials.find(
        {"id": {"$in": cred_ids}, "user_id": current_user["id"]}
    ).to_list(1000)
    cred_map = {c["id"]: c["api_name"] for c in credentials}

    result = []
    for e in events:
        e.pop("_id", None)
        e["api_name"] = cred_map.get(e["credential_id"], "unknown")
        result.append(e)

    return result


@router.get("/lifecycle/summary")
async def get_lifecycle_summary(
    current_user: dict = Depends(get_current_user),
):
    """Get lifecycle summary: events by type, most active credentials, credentials with no events."""
    user_id = current_user["id"]

    # Events by type count
    type_pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    type_results = await db.lifecycle_events.aggregate(type_pipeline).to_list(100)
    events_by_type = {r["_id"]: r["count"] for r in type_results}

    # Most active credentials (by event count)
    active_pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$credential_id", "event_count": {"$sum": 1}}},
        {"$sort": {"event_count": -1}},
        {"$limit": 5},
    ]
    active_results = await db.lifecycle_events.aggregate(active_pipeline).to_list(5)

    # Enrich with api_name
    active_cred_ids = [r["_id"] for r in active_results]
    credentials = await db.credentials.find(
        {"user_id": user_id}
    ).to_list(1000)
    cred_map = {c["id"]: c["api_name"] for c in credentials}

    most_active = []
    for r in active_results:
        most_active.append({
            "credential_id": r["_id"],
            "api_name": cred_map.get(r["_id"], "unknown"),
            "event_count": r["event_count"],
        })

    # Credentials with no lifecycle events
    all_cred_ids = {c["id"] for c in credentials}
    creds_with_events = {r["_id"] for r in active_results}

    # Get full list of creds with any events (not just top 5)
    all_events_pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$credential_id"}},
    ]
    all_event_creds = await db.lifecycle_events.aggregate(all_events_pipeline).to_list(1000)
    creds_with_events = {r["_id"] for r in all_event_creds}

    no_events = []
    for cred in credentials:
        if cred["id"] not in creds_with_events:
            no_events.append({
                "credential_id": cred["id"],
                "api_name": cred["api_name"],
            })

    total_events = sum(events_by_type.values())

    return {
        "total_events": total_events,
        "events_by_type": events_by_type,
        "most_active_credentials": most_active,
        "credentials_with_no_events": no_events,
    }
