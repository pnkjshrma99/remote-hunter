from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JobAnalytics(Base):
    __tablename__ = "job_analytics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Aggregation period
    period_start: Mapped[datetime] = mapped_column(DateTime, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime, index=True)
    period_type: Mapped[str] = mapped_column(String(32))  # daily, weekly, monthly
    
    # Metrics by category
    region: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    role_category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    company_size: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Counts
    total_jobs: Mapped[int] = mapped_column(Integer, default=0)
    new_jobs: Mapped[int] = mapped_column(Integer, default=0)
    remote_jobs: Mapped[int] = mapped_column(Integer, default=0)
    india_eligible: Mapped[int] = mapped_column(Integer, default=0)
    
    # Salary data (aggregated)
    avg_salary_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_salary_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Experience breakdown
    junior_count: Mapped[int] = mapped_column(Integer, default=0)
    mid_count: Mapped[int] = mapped_column(Integer, default=0)
    senior_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        {"comment": "Aggregated job analytics for dashboards and trends"},
    )


class SourcePerformance(Base):
    __tablename__ = "source_performance"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    
    # Performance metrics
    total_scraped: Mapped[int] = mapped_column(Integer, default=0)
    total_matched: Mapped[int] = mapped_column(Integer, default=0)
    match_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Quality metrics
    avg_relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    duplicate_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Response metrics
    avg_response_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    success_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Timestamps
    last_scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        {"comment": "Performance metrics for each job source"},
    )
