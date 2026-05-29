"""Extended user profile model for job application automation."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    # Personal info
    phone = Column(String(32), nullable=True)
    address = Column(String(500), nullable=True)
    city = Column(String(128), nullable=True)
    state = Column(String(128), nullable=True)
    postal_code = Column(String(32), nullable=True)
    country = Column(String(128), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    github_url = Column(String(500), nullable=True)
    portfolio_url = Column(String(500), nullable=True)
    website = Column(String(500), nullable=True)

    # Professional summary
    headline = Column(String(500), nullable=True)
    summary = Column(Text, nullable=True)

    # Work authorization
    authorized_to_work_in_us = Column(Boolean, default=False)
    visa_sponsorship_needed = Column(Boolean, default=False)
    currently_employed = Column(Boolean, default=False)
    notice_period_days = Column(Integer, nullable=True)

    # Job preferences
    desired_roles = Column(JSON, nullable=True)
    desired_salary_min = Column(Integer, nullable=True)
    desired_salary_max = Column(Integer, nullable=True)
    desired_salary_currency = Column(String(3), default="USD")
    preferred_locations = Column(JSON, nullable=True)
    remote_only = Column(Boolean, default=True)
    open_to_relocation = Column(Boolean, default=False)
    open_to_contract = Column(Boolean, default=True)
    open_to_fulltime = Column(Boolean, default=True)

    # Questions/answers for common application fields
    how_did_you_hear = Column(String(500), nullable=True)
    cover_letter_intro = Column(Text, nullable=True)
    additional_notes = Column(Text, nullable=True)

    # Demographic / EEO fields
    gender = Column(String(32), nullable=True)
    hispanic_latino = Column(String(32), nullable=True)
    veteran_status = Column(String(32), nullable=True)
    disability_status = Column(String(32), nullable=True)

    # Custom Q&A pairs for company-specific questions (e.g., "Why do you want to work here?")
    custom_answers = Column(JSON, nullable=True)  # {"Why Speechify?": "I love...", "Hardest problem": "..."}

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="profile")
    experiences = relationship("WorkExperience", back_populates="profile", cascade="all, delete-orphan")
    education = relationship("Education", back_populates="profile", cascade="all, delete-orphan")


class WorkExperience(Base):
    __tablename__ = "work_experiences"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False, index=True)

    company = Column(String(256), nullable=False)
    title = Column(String(256), nullable=False)
    location = Column(String(256), nullable=True)
    start_date = Column(String(32), nullable=False)
    end_date = Column(String(32), nullable=True)
    currently_working = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    tech_used = Column(JSON, nullable=True)
    achievements = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("UserProfile", back_populates="experiences")


class Education(Base):
    __tablename__ = "education"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False, index=True)

    school = Column(String(256), nullable=False)
    degree = Column(String(256), nullable=False)
    field_of_study = Column(String(256), nullable=True)
    location = Column(String(256), nullable=True)
    start_date = Column(String(32), nullable=False)
    end_date = Column(String(32), nullable=True)
    currently_studying = Column(Boolean, default=False)
    gpa = Column(String(8), nullable=True)
    achievements = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("UserProfile", back_populates="education")
