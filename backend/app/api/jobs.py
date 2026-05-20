from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.job import JobFilter, JobResponse, JobStats, JobUpdate, ScrapeRequest
from app.services.jobs import get_stats, list_jobs, run_scrape, update_job

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
