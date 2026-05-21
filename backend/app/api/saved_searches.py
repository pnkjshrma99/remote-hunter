"""Saved searches API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.saved_search import SavedSearch
from app.schemas.job import ScrapeRequest
from app.services.saved_searches import (
    create_saved_search,
    delete_saved_search,
    get_saved_search,
    get_user_saved_searches,
    run_saved_search,
    saved_search_to_scrape_request,
    update_saved_search,
)

router = APIRouter(prefix="/saved-searches", tags=["saved-searches"])


@router.post("/")
def create_search(
    user_email: str = Query(..., description="User email address"),
    name: str = Query(..., description="Name for the saved search"),
    scrape_request: ScrapeRequest = None,
    email_alerts_enabled: bool = Query(False, description="Enable email alerts"),
    alert_frequency: str = Query("daily", description="Alert frequency: daily, weekly, instant"),
    db: Session = Depends(get_db),
):
    """
    Create a new saved search.
    """
    if not scrape_request:
        scrape_request = ScrapeRequest()
    
    search = create_saved_search(
        db,
        user_email=user_email,
        name=name,
        scrape_request=scrape_request,
        email_alerts_enabled=email_alerts_enabled,
        alert_frequency=alert_frequency,
    )
    
    return search


@router.get("/")
def list_searches(
    user_email: str = Query(..., description="User email address"),
    db: Session = Depends(get_db),
):
    """
    Get all saved searches for a user.
    """
    return get_user_saved_searches(db, user_email)


@router.get("/{search_id}")
def get_search(search_id: int, db: Session = Depends(get_db)):
    """
    Get a specific saved search by ID.
    """
    search = get_saved_search(db, search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return search


@router.put("/{search_id}")
def update_search(
    search_id: int,
    name: str = Query(None, description="New name for the search"),
    email_alerts_enabled: bool = Query(None, description="Enable/disable email alerts"),
    alert_frequency: str = Query(None, description="Alert frequency"),
    db: Session = Depends(get_db),
):
    """
    Update a saved search.
    """
    kwargs = {}
    if name is not None:
        kwargs["name"] = name
    if email_alerts_enabled is not None:
        kwargs["email_alerts_enabled"] = email_alerts_enabled
    if alert_frequency is not None:
        kwargs["alert_frequency"] = alert_frequency
    
    search = update_saved_search(db, search_id, **kwargs)
    if not search:
        raise HTTPException(status_code=404, detail="Saved search not found")
    
    return search


@router.delete("/{search_id}")
def delete_search(search_id: int, db: Session = Depends(get_db)):
    """
    Delete (deactivate) a saved search.
    """
    success = delete_saved_search(db, search_id)
    if not success:
        raise HTTPException(status_code=404, detail="Saved search not found")
    
    return {"status": "success", "message": "Saved search deleted"}


@router.post("/{search_id}/run")
def run_search(search_id: int, db: Session = Depends(get_db)):
    """
    Run a saved search and get results.
    """
    result = run_saved_search(db, search_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result
