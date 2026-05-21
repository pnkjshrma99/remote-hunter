"""Job bundles API endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job_bundle import JobBundle
from app.services.job_bundles import (
    create_default_job_bundles,
    get_featured_job_bundles,
    get_job_bundle,
    increment_bundle_purchase,
    increment_bundle_view,
    list_job_bundles,
)

router = APIRouter(prefix="/job-bundles", tags=["job-bundles"])


@router.get("/")
def list_bundles(
    category: str = Query(None, description="Filter by category"),
    featured_only: bool = Query(False, description="Show only featured bundles"),
    free_only: bool = Query(False, description="Show only free bundles"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    List all job bundles with optional filters.
    """
    return list_job_bundles(db, category=category, featured_only=featured_only, free_only=free_only)


@router.get("/featured")
def featured_bundles(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """
    Get featured job bundles.
    """
    return get_featured_job_bundles(db, limit=limit)


@router.get("/{bundle_id}")
def get_bundle(bundle_id: int, db: Session = Depends(get_db)):
    """
    Get a specific job bundle by ID.
    """
    bundle = get_job_bundle(db, bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Job bundle not found")
    
    # Increment view count
    increment_bundle_view(db, bundle_id)
    
    # Parse JSON fields
    return {
        "id": bundle.id,
        "name": bundle.name,
        "description": bundle.description,
        "category": bundle.category,
        "price": bundle.price,
        "currency": bundle.currency,
        "is_free": bundle.is_free,
        "is_featured": bundle.is_featured,
        "included_items": json.loads(bundle.included_items) if bundle.included_items else [],
        "purchase_count": bundle.purchase_count,
        "view_count": bundle.view_count,
    }


@router.post("/{bundle_id}/purchase")
def purchase_bundle(bundle_id: int, db: Session = Depends(get_db)):
    """
    Record a bundle purchase (increment purchase count).
    """
    bundle = increment_bundle_purchase(db, bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Job bundle not found")
    
    return {"status": "success", "message": "Purchase recorded"}


@router.post("/initialize")
def initialize_bundles(db: Session = Depends(get_db)):
    """
    Initialize default job bundles.
    This should be called once during setup.
    """
    create_default_job_bundles(db)
    return {"status": "success", "message": "Job bundles initialized"}
