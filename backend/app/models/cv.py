"""CV model for storing uploaded resumes and parsed data."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class CV(Base):
    __tablename__ = "cvs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    cloudinary_url = Column(String(500), nullable=True)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    content_type = Column(String(100), nullable=False)
    
    # Parsed data
    parsed_data = Column(JSON, nullable=True)
    skills = Column(JSON, nullable=True)  # Array of strings
    tech_stack = Column(JSON, nullable=True)  # Array of strings
    job_roles = Column(JSON, nullable=True)  # Array of strings
    keywords = Column(JSON, nullable=True)  # Array of strings
    experience_years = Column(Integer, nullable=True)
    education = Column(JSON, nullable=True)  # Array of education objects
    certifications = Column(JSON, nullable=True)  # Array of strings
    
    # Metadata
    ats_score = Column(Integer, nullable=True)  # Overall ATS score (0-100)
    last_scraped_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="cvs")
    job_matches = relationship("CVJobMatch", back_populates="cv", cascade="all, delete-orphan")


class CVJobMatch(Base):
    __tablename__ = "cv_job_matches"

    id = Column(Integer, primary_key=True, index=True)
    cv_id = Column(Integer, ForeignKey("cvs.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    
    # Matching data
    match_score = Column(Integer, nullable=False)  # 0-100
    skills_matched = Column(JSON, nullable=True)  # Array of matched skills
    skills_missing = Column(JSON, nullable=True)  # Array of missing skills
    experience_match = Column(String(20), nullable=True)  # "high", "medium", "low"
    keyword_density = Column(JSON, nullable=True)  # Keyword analysis
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    cv = relationship("CV", back_populates="job_matches")
    job = relationship("Job", back_populates="cv_matches")
