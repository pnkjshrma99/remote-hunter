"""Saved searches service for user search configurations."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.saved_search import SavedSearch
from app.schemas.job import ScrapeRequest


def create_saved_search(
    db: Session,
    user_email: str,
    name: str,
    scrape_request: ScrapeRequest,
    email_alerts_enabled: bool = False,
    alert_frequency: str = "daily",
) -> SavedSearch:
    """
    Create a new saved search for a user.
    """
    saved_search = SavedSearch(
        user_email=user_email,
        name=name,
        query=scrape_request.query,
        job_profile_id=scrape_request.job_profile_id,
        min_experience=scrape_request.min_experience,
        max_experience=scrape_request.max_experience,
        posted_within_days=scrape_request.posted_within_days,
        remote_only=scrape_request.remote_only,
        global_or_india=scrape_request.global_or_india,
        exclude_indian_hq=scrape_request.exclude_indian_hq,
        strict_experience=scrape_request.strict_experience,
        strict_title=scrape_request.strict_title,
        strict_junior=scrape_request.strict_junior,
        sources=",".join(scrape_request.sources) if scrape_request.sources else None,
        email_alerts_enabled=email_alerts_enabled,
        alert_frequency=alert_frequency,
    )
    
    db.add(saved_search)
    db.flush()
    return saved_search


def get_user_saved_searches(db: Session, user_email: str) -> list[SavedSearch]:
    """
    Get all saved searches for a user.
    """
    searches = db.scalars(
        select(SavedSearch)
        .where(SavedSearch.user_email == user_email, SavedSearch.is_active == True)  # noqa: E712
        .order_by(SavedSearch.created_at.desc())
    ).all()
    
    return list(searches)


def get_saved_search(db: Session, search_id: int) -> Optional[SavedSearch]:
    """
    Get a specific saved search by ID.
    """
    return db.get(SavedSearch, search_id)


def update_saved_search(
    db: Session,
    search_id: int,
    **kwargs,
) -> Optional[SavedSearch]:
    """
    Update a saved search.
    """
    search = get_saved_search(db, search_id)
    if not search:
        return None
    
    for key, value in kwargs.items():
        if hasattr(search, key) and value is not None:
            setattr(search, key, value)
    
    db.flush()
    return search


def delete_saved_search(db: Session, search_id: int) -> bool:
    """
    Delete (deactivate) a saved search.
    """
    search = get_saved_search(db, search_id)
    if not search:
        return False
    
    search.is_active = False
    db.flush()
    return True


def saved_search_to_scrape_request(search: SavedSearch) -> ScrapeRequest:
    """
    Convert a saved search to a ScrapeRequest.
    """
    return ScrapeRequest(
        query=search.query or "",
        job_profile_id=search.job_profile_id,
        min_experience=search.min_experience,
        max_experience=search.max_experience,
        posted_within_days=search.posted_within_days,
        remote_only=search.remote_only,
        global_or_india=search.global_or_india,
        exclude_indian_hq=search.exclude_indian_hq,
        strict_experience=search.strict_experience,
        strict_title=search.strict_title,
        strict_junior=search.strict_junior,
        sources=search.sources.split(",") if search.sources else [],
        linkedin_urls=[],
    )


def run_saved_search(db: Session, search_id: int) -> dict:
    """
    Run a saved search and update match count.
    """
    from app.services.jobs import run_scrape
    
    search = get_saved_search(db, search_id)
    if not search:
        return {"error": "Search not found"}
    
    scrape_request = saved_search_to_scrape_request(search)
    
    # Run the scrape
    from app.database import SessionLocal
    scrape_db = SessionLocal()
    try:
        result = run_scrape(scrape_db, scrape_request, send_alerts=search.email_alerts_enabled)
        
        # Update match count
        search.last_match_count = result.get("jobs_new", 0)
        search.last_run_at = result.get("finished_at")
        
        return result
    finally:
        scrape_db.close()
