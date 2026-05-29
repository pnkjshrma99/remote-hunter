from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.deps import get_optional_user_id, get_required_user_id
from app.database import get_db, SessionLocal
from app.models.scrape_run import ScrapeRun
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
    user_id: int | None = Depends(get_optional_user_id),
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
    return list_jobs(db, filters, user_id=user_id)


@router.patch("/{job_id}", response_model=JobResponse)
def patch_job(
    job_id: int,
    payload: JobUpdate,
    user_id: int = Depends(get_required_user_id),
    db: Session = Depends(get_db),
):
    job = update_job(db, job_id, payload, user_id=user_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/stats", response_model=JobStats)
def stats(
    user_id: int | None = Depends(get_optional_user_id),
    db: Session = Depends(get_db),
):
    return get_stats(db, user_id=user_id)


@router.post("/scrape")
def scrape_now(
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_required_user_id),
    payload: ScrapeRequest | None = None,
    strict_junior: bool | None = None,
    send_alerts: bool | None = None,
    db: Session = Depends(get_db),
):
    """
    Run job scraper in background.
    
    Returns immediately with a scrape_run_id. Poll GET /scrape-runs for status.
    """
    from app.models.scrape_run import ScrapeRun

    scrape_run = ScrapeRun(status="queued")
    db.add(scrape_run)
    db.commit()
    db.refresh(scrape_run)
    run_id = scrape_run.id

    background_tasks.add_task(
        _run_scrape_background,
        run_id=run_id,
        user_id=user_id,
        payload=payload.model_dump() if payload else None,
        strict_junior=strict_junior,
        send_alerts=send_alerts,
    )

    return {
        "status": "queued",
        "scrape_run_id": run_id,
        "message": f"Scrape queued (run #{run_id}). Poll GET /scrape-runs/{run_id} for status."
    }


def _run_scrape_background(
    run_id: int,
    user_id: int,
    payload: dict | None,
    strict_junior: bool | None,
    send_alerts: bool | None,
) -> None:
    """Run scrape in a background thread with its own DB session."""
    db = SessionLocal()
    try:
        req = ScrapeRequest(**(payload or {}))
        result = run_scrape(
            db=db,
            request=req,
            strict_junior=strict_junior,
            send_alerts=send_alerts,
            user_id=user_id,
        )
        # Update the scrape run with actual results
        run = db.query(ScrapeRun).filter(ScrapeRun.id == run_id).first()
        if run:
            run.status = result.get("status", "failed")
            run.jobs_found = result.get("jobs_found", 0)
            run.jobs_new = result.get("jobs_new", 0)
            run.sources_run = ", ".join(result.get("sources_run", []))
            if result.get("status") == "failed":
                run.error_message = result.get("error", "")
            db.commit()
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.error(f"Background scrape run #{run_id} failed: {e}", exc_info=True)
        try:
            run = db.query(ScrapeRun).filter(ScrapeRun.id == run_id).first()
            if run:
                run.status = "failed"
                run.error_message = str(e)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.get("/scrape-runs/latest")
def get_latest_scrape_run(db: Session = Depends(get_db)):
    """Get the latest scrape run status."""
    run = db.query(ScrapeRun).order_by(ScrapeRun.started_at.desc()).first()
    if not run:
        return {"status": None, "message": "No scrape runs yet"}
    return {
        "id": run.id,
        "status": run.status,
        "jobs_found": run.jobs_found,
        "jobs_new": run.jobs_new,
        "sources_run": run.sources_run,
        "error_message": run.error_message,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


@router.get("/scrape-runs/{run_id}")
def get_scrape_run(run_id: int, db: Session = Depends(get_db)):
    """Get a specific scrape run by ID."""
    run = db.query(ScrapeRun).filter(ScrapeRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Scrape run not found")
    return {
        "id": run.id,
        "status": run.status,
        "jobs_found": run.jobs_found,
        "jobs_new": run.jobs_new,
        "sources_run": run.sources_run,
        "error_message": run.error_message,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


@router.get("/health")
def scraper_health():
    """Get health status of all job scrapers."""
    from scrapers.health_check import get_scraper_health, log_scraper_health_summary
    
    log_scraper_health_summary()
    return {
        "status": "ok",
        "scrapers": get_scraper_health(),
    }


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
