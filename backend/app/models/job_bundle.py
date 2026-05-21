from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JobBundle(Base):
    __tablename__ = "job_bundles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Bundle metadata
    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(128))  # devops, fullstack, etc.
    
    # Pricing
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    is_free: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Content (JSON as text)
    included_items: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of included items
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Metrics
    purchase_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        {"comment": "Remote-ready job package bundles for sale"},
    )
