from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.scrape_run import ScrapeRun

router = APIRouter(prefix="/scrape-runs", tags=["scrape runs"])


@router.get("")
def list_scrape_runs(limit: int = 20, db: Session = Depends(get_db)):
    stmt = select(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(limit)
    return list(db.scalars(stmt))
