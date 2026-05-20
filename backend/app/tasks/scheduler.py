import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
from app.database import SessionLocal
from app.schemas.job import ScrapeRequest
from app.services.jobs import run_scrape

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler = BackgroundScheduler(timezone="UTC")


def scheduled_scrape() -> None:
    db = SessionLocal()
    try:
        run_scrape(db, request=ScrapeRequest(send_alerts=True))
    finally:
        db.close()


def start_scheduler() -> None:
    if not settings.scrape_enabled:
        logger.info("Scheduler disabled via SCRAPE_ENABLED=false")
        return
    if scheduler.running:
        return
    scheduler.add_job(
        scheduled_scrape,
        IntervalTrigger(hours=settings.scrape_interval_hours),
        id="job_scraper",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("Scheduler started: every %s hours", settings.scrape_interval_hours)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
