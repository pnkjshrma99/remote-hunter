"""Company profiles API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Company
from app.services.companies import (
    get_company_jobs,
    get_company_stats,
    get_or_create_company,
    list_all_companies,
    search_companies,
    update_company_from_job,
)

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/")
def list_companies(
    search: str = Query(None, description="Search companies by name"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    List all companies with job listings.
    Optionally search by name.
    """
    if search:
        return search_companies(db, search, limit=limit)
    return list_all_companies(db, limit=limit)


@router.get("/{company_name}")
def get_company(company_name: str, db: Session = Depends(get_db)):
    """
    Get company profile with statistics and job listings.
    """
    stats = get_company_stats(db, company_name)
    jobs = get_company_jobs(db, company_name, limit=20)
    
    company = db.scalar(select(Company).where(Company.name == company_name))
    
    return {
        "profile": company,
        "stats": stats,
        "recent_jobs": jobs,
    }


@router.post("/{company_name}")
def create_or_update_company(
    company_name: str,
    db: Session = Depends(get_db),
):
    """
    Create or update a company profile.
    """
    company = get_or_create_company(db, company_name)
    return company
