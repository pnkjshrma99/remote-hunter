from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    website: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Company metadata
    industry: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    company_size: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    headquarters: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    founded_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Remote-specific info
    is_remote_friendly: Mapped[bool] = mapped_column(Boolean, default=True)
    remote_policy: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    regions_served: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    # Ratings and reviews
    overall_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Verification
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        {"comment": "Company profiles with ratings and remote-friendly status"},
    )
