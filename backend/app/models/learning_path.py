from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LearningPath(Base):
    __tablename__ = "learning_paths"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_profile_id: Mapped[str] = mapped_column(String(64), index=True)
    
    # Path metadata
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    difficulty_level: Mapped[str] = mapped_column(String(32), default="beginner")  # beginner, intermediate, advanced
    estimated_weeks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Content (JSON as text for simplicity)
    modules: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of modules
    resources: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of resources
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        {"comment": "Learning paths for job profiles with modules and resources"},
    )
