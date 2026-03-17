"""Project analysis routes for KeyForge."""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Dict
from datetime import datetime, timezone
import uuid
import logging

try:
    from ..config import db
    from ..models import ProjectCreate, ProjectAnalysis
    from ..security import get_current_user
    from ..patterns import API_PATTERNS, analyze_code_content
except ImportError:
    from backend.config import db
    from backend.models import ProjectCreate, ProjectAnalysis
    from backend.security import get_current_user
    from backend.patterns import API_PATTERNS, analyze_code_content

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["projects"])


@router.post("/projects/analyze", response_model=ProjectAnalysis)
async def analyze_project(
    project: ProjectCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a new project analysis for the authenticated user.

    Without file uploads, returns an analysis with empty detected APIs
    and a recommendation to upload project files.
    """
    analysis = ProjectAnalysis(
        id=str(uuid.uuid4()),
        project_name=project.project_name,
        detected_apis=[],
        file_count=0,
        analysis_timestamp=datetime.now(timezone.utc),
        recommendations=[
            "Upload project files to detect API usage",
        ],
    )

    analysis_doc = analysis.dict()
    analysis_doc["user_id"] = current_user["id"]

    await db.project_analyses.insert_one(analysis_doc)
    return analysis


@router.get("/projects/analyses", response_model=List[ProjectAnalysis])
async def get_project_analyses(
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """Get all project analyses for the authenticated user with pagination."""
    analyses = await (
        db.project_analyses
        .find({"user_id": current_user["id"]})
        .skip(skip)
        .limit(limit)
        .to_list(limit)
    )
    return [ProjectAnalysis(**a) for a in analyses]


@router.post("/projects/{project_id}/upload-files", response_model=dict)
async def upload_project_files(
    project_id: str,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload and analyze project files using real pattern detection."""
    detected_apis: List[Dict] = []
    file_count = len(files)

    for file in files:
        try:
            content = await file.read()
            content_str = content.decode("utf-8")
            file_detected = analyze_code_content(content_str, file.filename)
            detected_apis.extend(file_detected)
        except Exception as e:
            logger.warning("Could not analyze %s: %s", file.filename, str(e))

    # Remove duplicates and merge results
    unique_apis: Dict[str, Dict] = {}
    for api in detected_apis:
        key = api["api_id"]
        if key in unique_apis:
            unique_apis[key]["confidence"] = max(
                unique_apis[key]["confidence"], api["confidence"]
            )
            unique_apis[key]["matched_patterns"].extend(api["matched_patterns"])
        else:
            unique_apis[key] = api

    # Generate recommendations based on detected APIs
    recommendations = []
    for api in unique_apis.values():
        recommendations.append(
            f"Configure {api['name']} credentials for {api['category']} integration"
        )

    # Store the analysis result
    analysis_doc = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "project_name": project_id,
        "detected_apis": list(unique_apis.values()),
        "file_count": file_count,
        "analysis_timestamp": datetime.now(timezone.utc),
        "recommendations": recommendations,
    }
    await db.project_analyses.insert_one(analysis_doc)

    return {
        "detected_apis": list(unique_apis.values()),
        "file_count": file_count,
        "analysis_complete": True,
    }
