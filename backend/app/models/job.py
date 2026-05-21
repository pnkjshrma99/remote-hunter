from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(512))
    company: Mapped[str] = mapped_column(String(256), index=True)
    url: Mapped[str] = mapped_column(String(1024))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    salary: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    tech_stack: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    company_size: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    experience_level: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    region_eligibility: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Quality & Trust features
    is_verified_remote: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    seniority_tag: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)  # junior, mid, senior
    duplicate_group_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_sponsored: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_hot_job: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_applied: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    __table_args__ = (
        Index("ix_jobs_tech_stack", "tech_stack"),
        Index("ix_jobs_company_size", "company_size"),
    )
