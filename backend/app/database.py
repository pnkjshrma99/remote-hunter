import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

if settings.database_url.startswith("sqlite"):
    db_path = settings.database_url.replace("sqlite:///", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_existing_columns(table_name: str) -> set[str]:
    with engine.connect() as conn:
        result = conn.execute(text(f"PRAGMA table_info({table_name})"))
        return {row[1] for row in result}


def _ensure_job_columns():
    existing_columns = _get_existing_columns("jobs")
    if not existing_columns:
        return

    columns_to_add = {
        "is_verified_remote": "is_verified_remote INTEGER NOT NULL DEFAULT 0",
        "seniority_tag": "seniority_tag VARCHAR(32)",
        "duplicate_group_id": "duplicate_group_id VARCHAR(128)",
        "is_duplicate": "is_duplicate INTEGER NOT NULL DEFAULT 0",
        "is_sponsored": "is_sponsored INTEGER NOT NULL DEFAULT 0",
        "is_hot_job": "is_hot_job INTEGER NOT NULL DEFAULT 0",
    }

    with engine.begin() as conn:
        for column, definition in columns_to_add.items():
            if column not in existing_columns:
                conn.execute(text(f"ALTER TABLE jobs ADD COLUMN {definition}"))


def init_db():
    from app.models import (
        job,
        cover_letter,
        scrape_run,
        company,
        subscription,
        saved_search,
        learning_path,
        job_bundle,
        analytics,
    )  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_job_columns()
