import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.scrape_run import ScrapeRun
from app.services.user_jobs import get_applied_job_ids, overlay_applied_status, set_job_applied
from app.schemas.job import JobCreate, JobFilter, JobUpdate, ScrapeRequest
from app.services.notifications import notify_new_jobs
from app.services.quality_trust import (
    detect_seniority,
    is_verified_remote,
    generate_duplicate_signature,
)
from app.job_profiles import get_profile_by_id
from scrapers.filters import (
    RawJob,
    extract_tech_stack,
    infer_company_size,
    infer_experience_level,
    infer_region_eligibility,
)
from scrapers.schemas import SearchCriteria
from scrapers.registry import run_all_scrapers
from scrapers.pipeline import run_pipeline, PipelineResult
from scrapers.schemas import NormalizedJob
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    if value.isdigit():
        try:
            timestamp = int(value)
            if timestamp > 10_000_000_000:
                timestamp = timestamp // 1000
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(tzinfo=None)
        except (OSError, ValueError):
            return None
    cleaned = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        pass
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def _criteria_from_request(request: ScrapeRequest | None) -> SearchCriteria:
    request = request or ScrapeRequest()
    
    query = request.query
    min_exp = request.min_experience
    max_exp = request.max_experience
    
    if request.job_profile_id:
        profile = get_profile_by_id(request.job_profile_id)
        if profile:
            query = profile.name
            min_exp = profile.min_experience
            max_exp = profile.max_experience
    
    return SearchCriteria(
        query=query,
        job_profile_id=request.job_profile_id,
        min_experience=min_exp,
        max_experience=max_exp,
        posted_within_days=request.posted_within_days,
        remote_only=request.remote_only,
        global_or_india=request.global_or_india,
        exclude_indian_hq=request.exclude_indian_hq,
        strict_experience=request.strict_experience,
        strict_title=request.strict_title,
        linkedin_urls=request.linkedin_urls,
    )


def normalized_job_to_create(normalized: NormalizedJob) -> JobCreate:
    """Convert NormalizedJob to JobCreate for database storage."""
    seniority = normalized.seniority.value if normalized.seniority else None
    tech_stack = ", ".join(normalized.skills) if normalized.skills else None
    
    return JobCreate(
        external_id=normalized.external_id,
        source=normalized.source,
        title=normalized.title,
        company=normalized.company,
        url=normalized.url,
        description=normalized.description,
        location=normalized.location,
        salary=f"{normalized.salary_min}-{normalized.salary_max} {normalized.salary_currency}" if normalized.salary_min else "",
        tech_stack=tech_stack,
        company_size=None,
        experience_level=seniority,
        region_eligibility=None,
        posted_at=normalized.posted_at,
        is_verified_remote=normalized.remote_type.value == "fully_remote" if normalized.remote_type else False,
        seniority_tag=seniority,
        duplicate_group_id=normalized.duplicate_group_id,
        is_duplicate=normalized.is_duplicate,
        is_sponsored=False,
        is_hot_job=False,
        remote_type=normalized.remote_type.value if normalized.remote_type else None,
        job_type=normalized.job_type.value if normalized.job_type else None,
        experience_min_years=normalized.experience_min_years,
        experience_max_years=normalized.experience_max_years,
        salary_min=normalized.salary_min,
        salary_max=normalized.salary_max,
        salary_currency=normalized.salary_currency,
        skills=normalized.skills,
        tags=normalized.tags,
        responsibilities=normalized.responsibilities,
        requirements=normalized.requirements,
        relevance_score=normalized.relevance_score,
        confidence_score=normalized.confidence_score,
        is_likely_fake=normalized.is_likely_fake,
    )


def raw_job_to_create(raw: RawJob) -> JobCreate:
    combined = f"{raw.title} {raw.description} {raw.location}"
    
    seniority = detect_seniority(raw.title, raw.description)
    verified_remote = is_verified_remote(raw.location, raw.description, raw.title)
    duplicate_sig = generate_duplicate_signature(raw.title, raw.company, raw.description)
    
    return JobCreate(
        external_id=raw.external_id,
        source=raw.source,
        title=raw.title.strip(),
        company=raw.company.strip() or "Unknown",
        url=raw.url,
        description=raw.description,
        location=raw.location,
        salary=raw.salary,
        tech_stack=", ".join(extract_tech_stack(combined)),
        company_size=infer_company_size(raw.company, raw.description),
        experience_level=infer_experience_level(raw.title, raw.description),
        region_eligibility=infer_region_eligibility(raw.location, raw.description),
        posted_at=_parse_datetime(raw.posted_at),
        is_verified_remote=verified_remote,
        seniority_tag=seniority,
        duplicate_group_id=duplicate_sig,
        is_duplicate=False,
        is_sponsored=False,
        is_hot_job=False,
    )


def upsert_job(db: Session, payload: JobCreate) -> tuple[Job, bool]:
    existing = db.scalar(select(Job).where(Job.external_id == payload.external_id))
    if existing:
        for field, value in payload.model_dump().items():
            if value not in (None, ""):
                setattr(existing, field, value)
        existing.is_active = True
        return existing, False

    job = Job(**payload.model_dump())
    db.add(job)
    db.flush()
    return job, True


def batch_upsert_jobs(db: Session, payloads: List[JobCreate]) -> tuple[List[Job], List[Job]]:
    """Batch upsert jobs — single query to find existing, then bulk insert new."""
    if not payloads:
        return [], []

    ext_ids = [p.external_id for p in payloads]
    existing_map: Dict[str, Job] = {
        j.external_id: j
        for j in db.scalars(select(Job).where(Job.external_id.in_(ext_ids))).all()
    }

    updated: List[Job] = []
    new_jobs: List[Job] = []

    for payload in payloads:
        existing = existing_map.get(payload.external_id)
        if existing:
            for field, value in payload.model_dump().items():
                if value not in (None, ""):
                    setattr(existing, field, value)
            existing.is_active = True
            updated.append(existing)
        else:
            job = Job(**payload.model_dump())
            db.add(job)
            new_jobs.append(job)

    db.flush()
    return new_jobs, updated


def list_jobs(db: Session, filters: JobFilter, user_id: int | None = None) -> list[Job]:
    stmt = select(Job)
    conditions = []
    applied_job_ids: set[int] | None = None
    if user_id is not None:
        applied_job_ids = get_applied_job_ids(db, user_id)

    if filters.is_active is not None:
        conditions.append(Job.is_active == filters.is_active)
    if filters.is_applied is not None and applied_job_ids is not None:
        if filters.is_applied:
            if applied_job_ids:
                conditions.append(Job.id.in_(applied_job_ids))
            else:
                return []
        else:
            if applied_job_ids:
                conditions.append(~Job.id.in_(applied_job_ids))
    elif filters.is_applied is not None:
        conditions.append(Job.is_applied == filters.is_applied)
    if filters.source:
        conditions.append(Job.source.ilike(f"%{filters.source}%"))
    if filters.tech_stack:
        conditions.append(Job.tech_stack.ilike(f"%{filters.tech_stack}%"))
    if filters.company_size:
        conditions.append(Job.company_size == filters.company_size)
    if filters.experience_level:
        conditions.append(Job.experience_level == filters.experience_level)
    if filters.region_eligibility:
        conditions.append(Job.region_eligibility == filters.region_eligibility)
    if filters.is_verified_remote is not None:
        conditions.append(Job.is_verified_remote == filters.is_verified_remote)
    if filters.seniority_tag:
        conditions.append(Job.seniority_tag == filters.seniority_tag)
    if filters.is_duplicate is not None:
        conditions.append(Job.is_duplicate == filters.is_duplicate)
    if filters.is_sponsored is not None:
        conditions.append(Job.is_sponsored == filters.is_sponsored)
    if filters.is_hot_job is not None:
        conditions.append(Job.is_hot_job == filters.is_hot_job)
    if filters.search:
        term = f"%{filters.search}%"
        conditions.append(
            or_(Job.title.ilike(term), Job.company.ilike(term), Job.description.ilike(term))
        )

    if conditions:
        stmt = stmt.where(*conditions)

    stmt = stmt.order_by(Job.posted_at.desc().nullslast(), Job.scraped_at.desc())
    stmt = stmt.offset(filters.offset).limit(filters.limit)
    jobs = list(db.scalars(stmt))
    return overlay_applied_status(db, jobs, user_id)


def update_job(db: Session, job_id: int, payload: JobUpdate, user_id: int | None = None) -> Job | None:
    job = db.get(Job, job_id)
    if not job:
        return None

    data = payload.model_dump(exclude_unset=True)
    applied = data.pop("is_applied", None)

    if applied is not None:
        if user_id is None:
            return None
        if not set_job_applied(db, user_id, job_id, applied):
            return None

    for field, value in data.items():
        setattr(job, field, value)

    if applied is not None or data:
        db.commit()
        db.refresh(job)

    overlay_applied_status(db, [job], user_id)
    return job


def get_stats(db: Session, user_id: int | None = None) -> dict[str, Any]:
    jobs = list(db.scalars(select(Job).where(Job.is_active == True)))
    applied_job_ids = get_applied_job_ids(db, user_id) if user_id else set()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    tech_counter: Counter[str] = Counter()
    size_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()
    day_counter: defaultdict[str, int] = defaultdict(int)

    for job in jobs:
        for tech in (job.tech_stack or "Unknown").split(","):
            tech = tech.strip() or "Unknown"
            tech_counter[tech] += 1
        size_counter[job.company_size or "Unknown"] += 1
        source_counter[job.source] += 1
        day = (job.posted_at or job.scraped_at or now).date().isoformat()
        day_counter[day] += 1

    recent_days = {
        (now.date() - timedelta(days=i)).isoformat(): day_counter.get(
            (now.date() - timedelta(days=i)).isoformat(), 0
        )
        for i in reversed(range(14))
    }

    applied_count = (
        len(applied_job_ids)
        if user_id
        else sum(1 for job in jobs if job.is_applied)
    )

    return {
        "total_jobs": len(jobs),
        "applied_count": applied_count,
        "new_today": int(
            db.scalar(
                select(func.count())
                .select_from(Job)
                .where(Job.scraped_at >= today_start, Job.is_active == True)
            )
            or 0
        ),
        "by_tech_stack": dict(tech_counter.most_common()),
        "by_company_size": dict(size_counter.most_common()),
        "by_day": recent_days,
        "by_source": dict(source_counter.most_common()),
    }


def mark_hot_jobs(db: Session) -> int:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    week_ago = now - timedelta(days=7)
    
    db.query(Job).update({Job.is_hot_job: False})
    
    hot_jobs = db.scalars(
        select(Job)
        .where(
            Job.is_active == True,
            Job.is_duplicate == False,
            Job.is_verified_remote == True,
            Job.posted_at >= week_ago
        )
        .order_by(Job.posted_at.desc())
        .limit(20)
    ).all()
    
    for job in hot_jobs:
        job.is_hot_job = True
    
    db.commit()
    return len(hot_jobs)


def get_hot_jobs(db: Session, limit: int = 10) -> list[Job]:
    jobs = db.scalars(
        select(Job)
        .where(Job.is_hot_job == True, Job.is_active == True)
        .order_by(Job.posted_at.desc())
        .limit(limit)
    ).all()
    
    return list(jobs)


def run_scrape_with_pipeline(
    db: Session,
    request: ScrapeRequest | None = None,
    strict_junior: bool | None = None,
    send_alerts: bool | None = None,
    user_id: int | None = None,
    use_new_pipeline: bool = True,
) -> dict[str, Any]:
    request = request or ScrapeRequest()
    if strict_junior is not None:
        request.strict_junior = strict_junior
    if send_alerts is not None:
        request.send_alerts = send_alerts
    
    criteria = _criteria_from_request(request)
    scrape_run = ScrapeRun(status="running")
    db.add(scrape_run)
    db.commit()
    db.refresh(scrape_run)

    start_time = datetime.utcnow()
    
    try:
        if use_new_pipeline:
            logger.info("Using new scraping pipeline")
            pipeline_result = run_pipeline(
                criteria=criteria,
                source_names=request.sources or None,
                max_results=500,
                enable_description_fetch=False,
            )
            
            if not pipeline_result.success:
                raise Exception(pipeline_result.error or "Pipeline failed")
            
            normalized_jobs = pipeline_result.jobs
            logger.info(f"Pipeline returned {len(normalized_jobs)} jobs")
        else:
            logger.info("Using legacy scraping pipeline")
            raw_jobs = run_all_scrapers(
                strict_junior=request.strict_junior,
                criteria=criteria,
                source_names=request.sources or None,
            )
            normalized_jobs = [NormalizedJob.from_raw_job(job) for job in raw_jobs]
        
        # Batch upsert all jobs — single SELECT query instead of one per job
        sources = sorted({job.source for job in normalized_jobs})
        verified_remote_count = 0
        
        payloads = [normalized_job_to_create(job) for job in normalized_jobs]
        for p in payloads:
            if p.is_verified_remote:
                verified_remote_count += 1
        
        new_jobs, _ = batch_upsert_jobs(db, payloads)
        
        # Atomically deactivate old & reactivate current jobs
        if normalized_jobs:
            external_ids = [j.external_id for j in normalized_jobs]
            db.query(Job).update({Job.is_active: False})
            db.query(Job).filter(Job.external_id.in_(external_ids)).update(
                {Job.is_active: True}, synchronize_session=False
            )
            db.flush()

        scrape_run.status = "success"
        scrape_run.jobs_found = len(normalized_jobs)
        scrape_run.jobs_new = len(new_jobs)
        scrape_run.sources_run = ", ".join(sources)
        scrape_run.finished_at = datetime.utcnow()
        db.commit()

        if request.send_alerts:
            notify_new_jobs(new_jobs)

        try:
            hot_count = mark_hot_jobs(db)
            logger.info(f"Marked {hot_count} jobs as hot")
        except Exception as hot_error:
            logger.warning(f"Failed to mark hot jobs: {hot_error}")

        from scrapers.health_check import log_scraper_health_summary
        log_scraper_health_summary()

        duration = round((datetime.utcnow() - start_time).total_seconds(), 2)
        logger.info("Scrape complete: %d found, %d new", len(normalized_jobs), len(new_jobs))
        
        result = {
            "status": "success",
            "jobs_found": len(normalized_jobs),
            "jobs_new": len(new_jobs),
            "verified_remote_jobs": verified_remote_count,
            "sources_run": sources,
            "total_sources": len(sources),
            "query": request.query,
            "duration_seconds": duration,
            "pipeline_used": "new" if use_new_pipeline else "legacy",
        }
        
        if use_new_pipeline:
            result["pipeline_metrics"] = pipeline_result.to_dict()
        
        return result
        
    except Exception as exc:
        db.rollback()
        scrape_run.status = "failed"
        scrape_run.error_message = str(exc)
        scrape_run.finished_at = datetime.utcnow()
        db.add(scrape_run)
        db.commit()
        logger.exception("Scrape failed")
        return {"status": "failed", "error": str(exc)}


def get_scrape_freshness(db: Session) -> dict:
    """Return the last successful scrape time and whether jobs are stale."""
    last_run = db.query(ScrapeRun).filter(
        ScrapeRun.status == "success",
        ScrapeRun.finished_at.isnot(None)
    ).order_by(ScrapeRun.finished_at.desc()).first()

    active_count = db.query(Job).filter(Job.is_active == True).count()
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=settings.scrape_interval_hours)

    if last_run and last_run.finished_at:
        is_fresh = last_run.finished_at > cutoff
    else:
        is_fresh = False

    return {
        "last_scrape_at": last_run.finished_at.isoformat() if last_run and last_run.finished_at else None,
        "is_fresh": is_fresh,
        "active_jobs_count": active_count,
        "stale_in_hours": round((now - (last_run.finished_at if last_run and last_run.finished_at else now)).total_seconds() / 3600, 1) if last_run and last_run.finished_at else None,
    }


def run_scrape(
    db: Session,
    request: ScrapeRequest | None = None,
    strict_junior: bool | None = None,
    send_alerts: bool | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    return run_scrape_with_pipeline(
        db=db,
        request=request,
        strict_junior=strict_junior,
        send_alerts=send_alerts,
        user_id=user_id,
        use_new_pipeline=True,
    )