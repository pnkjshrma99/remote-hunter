import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

if settings.database_url.startswith("sqlite"):
    db_path = settings.database_url.replace("sqlite:///", "")
    # Convert to absolute path to avoid working directory issues
    if not os.path.isabs(db_path):
        db_path = os.path.abspath(db_path)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=settings.debug,
)

# Enable WAL mode for better concurrency and data integrity
if settings.database_url.startswith("sqlite"):
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA synchronous=NORMAL"))
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.commit()

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


def _ensure_columns(table_name: str, columns_to_add: dict[str, str]) -> None:
    existing_columns = _get_existing_columns(table_name)
    if not existing_columns:
        return

    with engine.begin() as conn:
        for column, definition in columns_to_add.items():
            if column not in existing_columns:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {definition}"))


def _ensure_job_columns():
    _ensure_columns(
        "jobs",
        {
            "is_verified_remote": "is_verified_remote INTEGER NOT NULL DEFAULT 0",
            "seniority_tag": "seniority_tag VARCHAR(32)",
            "duplicate_group_id": "duplicate_group_id VARCHAR(128)",
            "is_duplicate": "is_duplicate INTEGER NOT NULL DEFAULT 0",
            "is_sponsored": "is_sponsored INTEGER NOT NULL DEFAULT 0",
            "is_hot_job": "is_hot_job INTEGER NOT NULL DEFAULT 0",
        },
    )


def _ensure_cover_letter_user_id():
    """Add user_id to legacy templates; orphan rows (user_id=0) are hidden from all users."""
    _ensure_columns("cover_letter_templates", {"user_id": "user_id INTEGER NOT NULL DEFAULT 0"})


def _ensure_cv_columns():
    """Add job_roles and keywords columns to cvs table."""
    _ensure_columns(
        "cvs",
        {
            "job_roles": "job_roles JSON",
            "keywords": "keywords JSON",
        },
    )


def _ensure_user_name_columns():
    _ensure_columns(
        "users",
        {
            "first_name": "first_name VARCHAR(128)",
            "last_name": "last_name VARCHAR(128)",
            "middle_name": "middle_name VARCHAR(128)",
        },
    )


def _ensure_user_profile_columns():
    _ensure_columns(
        "user_profiles",
        {
            "gender": "gender VARCHAR(32)",
            "hispanic_latino": "hispanic_latino VARCHAR(32)",
            "veteran_status": "veteran_status VARCHAR(32)",
            "disability_status": "disability_status VARCHAR(32)",
            "custom_answers": "custom_answers JSON",
            "state": "state VARCHAR(128)",
            "postal_code": "postal_code VARCHAR(32)",
        },
    )


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
        user,
        user_job,  # noqa: F401
        cv,  # noqa: F401
        user_profile,  # noqa: F401
        api_token,  # noqa: F401
    )  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_job_columns()
    _ensure_cover_letter_user_id()
    _ensure_cv_columns()
    _ensure_user_name_columns()
    _ensure_user_profile_columns()
