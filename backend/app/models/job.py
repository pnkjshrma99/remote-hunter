from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Index, String, Text, Float, Integer, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    # New normalized fields
    remote_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # fully_remote, hybrid, onsite
    job_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # full_time, part_time, contract
    experience_min_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    experience_max_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(8), nullable=True, default="USD")
    skills: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Stored as JSON array
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Stored as JSON array
    responsibilities: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Stored as JSON array
    requirements: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Stored as JSON array
    
    # Scoring
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_likely_fake: Mapped[bool] = mapped_column(Boolean, default=False)

    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_applied: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Relationships
    cv_matches = relationship("CVJobMatch", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_jobs_tech_stack", "tech_stack"),
        Index("ix_jobs_company_size", "company_size"),
    )
