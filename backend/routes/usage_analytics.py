"""Usage analytics routes for KeyForge."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

try:
    from ..config import db
    from ..security import get_current_user
except ImportError:
    from backend.config import db
    from backend.security import get_current_user

router = APIRouter(prefix="/api", tags=["usage-analytics"])

VALID_ACTIONS = ["tested", "viewed", "exported", "shared", "rotated"]


class TrackUsageRequest(BaseModel):
    credential_id: str
    action: str


@router.post("/usage/track", response_model=dict)
async def track_usage(
    body: TrackUsageRequest,
    current_user: dict = Depends(get_current_user),
):
    """Record a usage event for a credential."""
    if body.action not in VALID_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"action must be one of: {', '.join(VALID_ACTIONS)}",
        )

    # Verify credential belongs to user
    credential = await db.credentials.find_one(
        {
            "id": body.credential_id,
            "user_id": current_user["id"],
        }
    )
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    event_doc = {
        "id": str(uuid.uuid4()),
        "credential_id": body.credential_id,
        "user_id": current_user["id"],
        "action": body.action,
        "timestamp": datetime.now(timezone.utc),
    }
    await db.usage_events.insert_one(event_doc)

    return {"message": "Usage event recorded", "event_id": event_doc["id"]}


async def _compute_analytics_for_credential(credential: dict, user_id: str) -> dict:
    """Compute usage analytics for a single credential."""
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    credential_id = credential["id"]

    # Aggregation pipeline for this credential
    pipeline = [
        {"$match": {"credential_id": credential_id, "user_id": user_id}},
        {
            "$group": {
                "_id": None,
                "total_uses": {"$sum": 1},
                "last_used": {"$max": "$timestamp"},
                "uses_last_7_days": {"$sum": {"$cond": [{"$gte": ["$timestamp", seven_days_ago]}, 1, 0]}},
                "uses_last_30_days": {"$sum": {"$cond": [{"$gte": ["$timestamp", thirty_days_ago]}, 1, 0]}},
            }
        },
    ]

    results = await db.usage_events.aggregate(pipeline).to_list(1)

    if results:
        r = results[0]
        last_used = r.get("last_used")
        is_idle = last_used < thirty_days_ago if last_used else True
        return {
            "credential_id": credential_id,
            "api_name": credential["api_name"],
            "total_uses": r["total_uses"],
            "last_used": last_used,
            "uses_last_7_days": r["uses_last_7_days"],
            "uses_last_30_days": r["uses_last_30_days"],
            "is_idle": is_idle,
        }
    else:
        return {
            "credential_id": credential_id,
            "api_name": credential["api_name"],
            "total_uses": 0,
            "last_used": None,
            "uses_last_7_days": 0,
            "uses_last_30_days": 0,
            "is_idle": True,
        }


@router.get("/usage/analytics", response_model=list[dict])
async def get_usage_analytics(
    current_user: dict = Depends(get_current_user),
):
    """Get usage analytics for all user's credentials."""
    credentials = await db.credentials.find({"user_id": current_user["id"]}).to_list(1000)

    analytics = []
    for cred in credentials:
        a = await _compute_analytics_for_credential(cred, current_user["id"])
        analytics.append(a)

    return analytics


@router.get("/usage/analytics/{credential_id}", response_model=dict)
async def get_credential_usage_analytics(
    credential_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get detailed usage analytics for a specific credential."""
    credential = await db.credentials.find_one(
        {
            "id": credential_id,
            "user_id": current_user["id"],
        }
    )
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    analytics = await _compute_analytics_for_credential(credential, current_user["id"])

    # Also include recent events
    recent_events = (
        await db.usage_events.find({"credential_id": credential_id, "user_id": current_user["id"]})
        .sort("timestamp", -1)
        .limit(50)
        .to_list(50)
    )

    for e in recent_events:
        e.pop("_id", None)

    analytics["recent_events"] = recent_events
    return analytics


@router.get("/usage/idle-credentials", response_model=list[dict])
async def get_idle_credentials(
    current_user: dict = Depends(get_current_user),
):
    """Get credentials with no usage in 30+ days."""
    credentials = await db.credentials.find({"user_id": current_user["id"]}).to_list(1000)

    idle = []
    for cred in credentials:
        a = await _compute_analytics_for_credential(cred, current_user["id"])
        if a["is_idle"]:
            idle.append(a)

    return idle


@router.get("/usage/dashboard", response_model=dict)
async def get_usage_dashboard(
    current_user: dict = Depends(get_current_user),
):
    """Get dashboard-level usage stats."""
    user_id = current_user["id"]
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    credentials = await db.credentials.find({"user_id": user_id}).to_list(1000)

    total_credentials = len(credentials)
    cred_ids = [c["id"] for c in credentials]
    cred_map = {c["id"]: c["api_name"] for c in credentials}

    if not cred_ids:
        return {
            "total_credentials": 0,
            "active_count": 0,
            "idle_count": 0,
            "most_used": [],
            "never_used": [],
        }

    # Aggregation: group usage events by credential_id
    pipeline = [
        {"$match": {"user_id": user_id, "credential_id": {"$in": cred_ids}}},
        {
            "$group": {
                "_id": "$credential_id",
                "total_uses": {"$sum": 1},
                "last_used": {"$max": "$timestamp"},
                "uses_last_7_days": {"$sum": {"$cond": [{"$gte": ["$timestamp", seven_days_ago]}, 1, 0]}},
            }
        },
        {"$sort": {"total_uses": -1}},
    ]

    usage_results = await db.usage_events.aggregate(pipeline).to_list(1000)
    usage_by_cred = {r["_id"]: r for r in usage_results}

    active_count = 0
    idle_count = 0
    never_used = []
    most_used = []

    for cred_id in cred_ids:
        if cred_id in usage_by_cred:
            u = usage_by_cred[cred_id]
            if u.get("uses_last_7_days", 0) > 0:
                active_count += 1
            last_used = u.get("last_used")
            if last_used and last_used < thirty_days_ago:
                idle_count += 1
        else:
            never_used.append(
                {
                    "credential_id": cred_id,
                    "api_name": cred_map.get(cred_id, "unknown"),
                }
            )
            idle_count += 1

    # Top 5 most used
    for r in usage_results[:5]:
        most_used.append(
            {
                "credential_id": r["_id"],
                "api_name": cred_map.get(r["_id"], "unknown"),
                "total_uses": r["total_uses"],
            }
        )

    return {
        "total_credentials": total_credentials,
        "active_count": active_count,
        "idle_count": idle_count,
        "most_used": most_used,
        "never_used": never_used,
    }
