"""Dashboard routes for KeyForge."""

from fastapi import APIRouter, Depends
from typing import Dict

try:
    from ..config import db
    from ..models import ProjectAnalysis
    from ..security import get_current_user
    from ..patterns import API_PATTERNS
except ImportError:
    from backend.config import db
    from backend.models import ProjectAnalysis
    from backend.security import get_current_user
    from backend.patterns import API_PATTERNS

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard/overview", response_model=dict)
async def get_dashboard_overview(
    current_user: dict = Depends(get_current_user),
):
    """Get dashboard overview data for the authenticated user."""
    # Get only this user's credentials
    credentials = await (
        db.credentials
        .find({"user_id": current_user["id"]})
        .to_list(1000)
    )
    total_credentials = len(credentials)

    status_counts: Dict[str, int] = {}
    for cred in credentials:
        status = cred.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    # Get recent analyses for this user
    recent_analyses = await (
        db.project_analyses
        .find({"user_id": current_user["id"]})
        .sort("analysis_timestamp", -1)
        .limit(5)
        .to_list(5)
    )

    # Calculate health score
    active_count = status_counts.get("active", 0)
    health_score = (active_count / max(total_credentials, 1)) * 100

    return {
        "total_credentials": total_credentials,
        "status_breakdown": status_counts,
        "health_score": round(health_score, 1),
        "recent_analyses": [ProjectAnalysis(**a) for a in recent_analyses],
        "recommendations": [
            "Test inactive credentials",
            "Update expired API keys",
            "Add missing environment variables",
            "Configure webhook endpoints",
        ],
    }


@router.get("/api-catalog", response_model=dict)
async def get_api_catalog(
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """Get available API catalog with pagination."""
    catalog = []
    for api_id, config in API_PATTERNS.items():
        catalog.append({
            "id": api_id,
            "name": config["name"],
            "category": config["category"],
            "auth_type": config["auth_type"],
            "available_scopes": config["scopes"],
            "description": f"{config['name']} integration for {config['category']}",
        })

    # Apply pagination to the catalog list
    paginated = catalog[skip : skip + limit]
    return {"apis": paginated, "total": len(catalog)}
