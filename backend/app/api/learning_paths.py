"""Learning paths API endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.learning_path import LearningPath
from app.services.learning_paths import (
    create_default_learning_paths,
    get_featured_learning_paths,
    get_learning_path,
    list_learning_paths,
)

router = APIRouter(prefix="/learning-paths", tags=["learning-paths"])


@router.get("/")
def list_paths(
    featured_only: bool = Query(False, description="Show only featured paths"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    List all learning paths.
    """
    if featured_only:
        return get_featured_learning_paths(db, limit=limit)
    return list_learning_paths()


@router.get("/{job_profile_id}")
def get_path(job_profile_id: str, db: Session = Depends(get_db)):
    """
    Get learning path for a specific job profile.
    """
    path = get_learning_path(db, job_profile_id)
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")
    
    # Parse JSON fields
    return {
        "id": path.id,
        "job_profile_id": path.job_profile_id,
        "title": path.title,
        "description": path.description,
        "difficulty_level": path.difficulty_level,
        "estimated_weeks": path.estimated_weeks,
        "modules": json.loads(path.modules) if path.modules else [],
        "resources": json.loads(path.resources) if path.resources else [],
        "is_featured": path.is_featured,
    }


@router.post("/initialize")
def initialize_paths(db: Session = Depends(get_db)):
    """
    Initialize default learning paths for all job profiles.
    This should be called once during setup.
    """
    create_default_learning_paths(db)
    return {"status": "success", "message": "Learning paths initialized"}
