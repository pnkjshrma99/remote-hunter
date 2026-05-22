from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.user_job import UserJobApplication


def get_applied_job_ids(db: Session, user_id: int) -> set[int]:
    rows = db.scalars(
        select(UserJobApplication.job_id).where(UserJobApplication.user_id == user_id)
    )
    return set(rows)


def set_job_applied(db: Session, user_id: int, job_id: int, is_applied: bool) -> bool:
    """Set or clear applied status for a user. Returns False if job does not exist."""
    job = db.get(Job, job_id)
    if not job:
        return False

    existing = db.scalar(
        select(UserJobApplication).where(
            UserJobApplication.user_id == user_id,
            UserJobApplication.job_id == job_id,
        )
    )

    if is_applied:
        if not existing:
            db.add(UserJobApplication(user_id=user_id, job_id=job_id))
    elif existing:
        db.delete(existing)

    return True


def overlay_applied_status(db: Session, jobs: list[Job], user_id: int | None) -> list[Job]:
    """Attach per-user is_applied onto job instances for API responses."""
    if not user_id or not jobs:
        for job in jobs:
            job.is_applied = False
        return jobs

    applied_ids = get_applied_job_ids(db, user_id)
    for job in jobs:
        job.is_applied = job.id in applied_ids
    return jobs
