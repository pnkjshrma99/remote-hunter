from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_email: Mapped[str] = mapped_column(String(256), index=True)
    
    # Search configuration
    name: Mapped[str] = mapped_column(String(256))
    query: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    job_profile_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Filters
    min_experience: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_experience: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    posted_within_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    remote_only: Mapped[bool] = mapped_column(Boolean, default=True)
    global_or_india: Mapped[bool] = mapped_column(Boolean, default=True)
    exclude_indian_hq: Mapped[bool] = mapped_column(Boolean, default=False)
    strict_experience: Mapped[bool] = mapped_column(Boolean, default=False)
    strict_title: Mapped[bool] = mapped_column(Boolean, default=False)
    strict_junior: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Sources (comma-separated)
    sources: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Alert settings
    email_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_frequency: Mapped[str] = mapped_column(String(32), default="daily")  # daily, weekly, instant
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_match_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        {"comment": "User saved search configurations with alert settings"},
    )
