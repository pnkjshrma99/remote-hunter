from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.schemas.job import JobFilter, JobResponse, JobStats, JobUpdate, ScrapeRequest
from app.services.jobs import get_hot_jobs, get_stats, list_jobs, mark_hot_jobs, run_scrape, update_job
from app.job_profiles import JOB_PROFILES, get_all_categories, list_all_profiles, get_profile_by_id

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobResponse])
def read_jobs(
    search: str | None = None,
    source: str | None = None,
    tech_stack: str | None = None,
    company_size: str | None = None,
    experience_level: str | None = None,
    region_eligibility: str | None = None,
    is_applied: bool | None = None,
    is_active: bool = True,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    filters = JobFilter(
        search=search,
        source=source,
        tech_stack=tech_stack,
        company_size=company_size,
        experience_level=experience_level,
        region_eligibility=region_eligibility,
        is_applied=is_applied,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return list_jobs(db, filters)


@router.patch("/{job_id}", response_model=JobResponse)
def patch_job(job_id: int, payload: JobUpdate, db: Session = Depends(get_db)):
    job = update_job(db, job_id, payload)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/stats", response_model=JobStats)
def stats(db: Session = Depends(get_db)):
    return get_stats(db)


@router.post("/scrape")
def scrape_now(
    payload: ScrapeRequest | None = None,
    strict_junior: bool | None = None,
    send_alerts: bool | None = None,
    db: Session = Depends(get_db),
):
    return run_scrape(
        db,
        request=payload,
        strict_junior=strict_junior,
        send_alerts=send_alerts,
    )


# ============================================================================
# Job Profile Endpoints
# ============================================================================


class JobProfileResponse(BaseModel):
    id: str
    name: str
    keywords: list[str]
    description: str
    min_experience: int
    max_experience: int
    role_category: str


class CategoryResponse(BaseModel):
    categories: list[str]


@router.get("/profiles/list", response_model=list[JobProfileResponse])
def list_job_profiles():
    """List all available job profiles."""
    profiles = list_all_profiles()
    return [
        JobProfileResponse(
            id=p.id,
            name=p.name,
            keywords=p.keywords,
            description=p.description,
            min_experience=p.min_experience,
            max_experience=p.max_experience,
            role_category=p.role_category,
        )
        for p in profiles
    ]


@router.get("/profiles/{profile_id}", response_model=JobProfileResponse)
def get_job_profile(profile_id: str):
    """Get a specific job profile by ID."""
    profile = get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
    return JobProfileResponse(
        id=profile.id,
        name=profile.name,
        keywords=profile.keywords,
        description=profile.description,
        min_experience=profile.min_experience,
        max_experience=profile.max_experience,
        role_category=profile.role_category,
    )


@router.get("/profiles/categories/list", response_model=CategoryResponse)
def list_categories():
    """List all job profile categories."""
    return CategoryResponse(categories=get_all_categories())


@router.get("/hot", response_model=list[JobResponse])
def get_hot_jobs_endpoint(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Get hot jobs - recently posted, verified remote, high quality."""
    return get_hot_jobs(db, limit=limit)


@router.post("/hot/mark")
def mark_hot_jobs_endpoint(db: Session = Depends(get_db)):
    """Mark jobs as hot based on criteria. Should be called periodically."""
    count = mark_hot_jobs(db)
    return {"status": "success", "marked_count": count}
