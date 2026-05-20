import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.scrape_run import ScrapeRun
from app.schemas.job import JobCreate, JobFilter, JobUpdate, ScrapeRequest
from app.services.notifications import notify_new_jobs
from scrapers.filters import (
    RawJob,
    SearchCriteria,
    extract_tech_stack,
    infer_company_size,
    infer_experience_level,
    infer_region_eligibility,
)
from scrapers.registry import run_all_scrapers

logger = logging.getLogger(__name__)


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
    return SearchCriteria(
        query=request.query,
        min_experience=request.min_experience,
        max_experience=request.max_experience,
        posted_within_days=request.posted_within_days,
        remote_only=request.remote_only,
        global_or_india=request.global_or_india,
        exclude_indian_hq=request.exclude_indian_hq,
        strict_experience=request.strict_experience,
        strict_title=request.strict_title,
        linkedin_urls=request.linkedin_urls,
    )


def raw_job_to_create(raw: RawJob) -> JobCreate:
    combined = f"{raw.title} {raw.description} {raw.location}"
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


def list_jobs(db: Session, filters: JobFilter) -> list[Job]:
    stmt = select(Job)
    conditions = []

    if filters.is_active is not None:
        conditions.append(Job.is_active == filters.is_active)
    if filters.is_applied is not None:
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
    if filters.search:
        term = f"%{filters.search}%"
        conditions.append(
            or_(Job.title.ilike(term), Job.company.ilike(term), Job.description.ilike(term))
        )

    if conditions:
        stmt = stmt.where(*conditions)

    stmt = stmt.order_by(Job.posted_at.desc().nullslast(), Job.scraped_at.desc())
    stmt = stmt.offset(filters.offset).limit(filters.limit)
    return list(db.scalars(stmt))


def update_job(db: Session, job_id: int, payload: JobUpdate) -> Job | None:
    job = db.get(Job, job_id)
    if not job:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    db.commit()
    db.refresh(job)
    return job


def get_stats(db: Session) -> dict[str, Any]:
    jobs = list(db.scalars(select(Job).where(Job.is_active == True)))  # noqa: E712
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

    return {
        "total_jobs": len(jobs),
        "applied_count": sum(1 for job in jobs if job.is_applied),
        "new_today": int(
            db.scalar(
                select(func.count())
                .select_from(Job)
                .where(Job.scraped_at >= today_start, Job.is_active == True)  # noqa: E712
            )
            or 0
        ),
        "by_tech_stack": dict(tech_counter.most_common()),
        "by_company_size": dict(size_counter.most_common()),
        "by_day": recent_days,
        "by_source": dict(source_counter.most_common()),
    }


def run_scrape(
    db: Session,
    request: ScrapeRequest | None = None,
    strict_junior: bool | None = None,
    send_alerts: bool | None = None,
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

    try:
        raw_jobs = run_all_scrapers(
            strict_junior=request.strict_junior,
            criteria=criteria,
            source_names=request.sources or None,
        )
        new_jobs: list[Job] = []
        sources = sorted({job.source for job in raw_jobs})

        db.query(Job).update({Job.is_active: False})
        for raw in raw_jobs:
            job, created = upsert_job(db, raw_job_to_create(raw))
            if created:
                new_jobs.append(job)

        scrape_run.status = "success"
        scrape_run.jobs_found = len(raw_jobs)
        scrape_run.jobs_new = len(new_jobs)
        scrape_run.sources_run = ", ".join(sources)
        scrape_run.finished_at = datetime.utcnow()
        db.commit()

        for job in new_jobs:
            db.refresh(job)

        if request.send_alerts:
            notify_new_jobs(new_jobs)

        logger.info("Scrape complete: %d found, %d new", len(raw_jobs), len(new_jobs))
        return {
            "status": "success",
            "jobs_found": len(raw_jobs),
            "jobs_new": len(new_jobs),
            "sources_run": sources,
            "query": request.query,
        }
    except Exception as exc:
        db.rollback()
        scrape_run.status = "failed"
        scrape_run.error_message = str(exc)
        scrape_run.finished_at = datetime.utcnow()
        db.add(scrape_run)
        db.commit()
        logger.exception("Scrape failed")
        return {"status": "failed", "error": str(exc)}
