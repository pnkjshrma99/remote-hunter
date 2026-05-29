"""Pydantic schemas for extended user profile."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class WorkExperienceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    profile_id: Optional[int] = None
    company: str
    title: str
    location: Optional[str] = None
    start_date: str
    end_date: Optional[str] = None
    currently_working: bool = False
    description: Optional[str] = None
    tech_used: Optional[List[str]] = None
    achievements: Optional[List[str]] = None


class WorkExperienceCreate(BaseModel):
    company: str
    title: str
    location: Optional[str] = None
    start_date: str
    end_date: Optional[str] = None
    currently_working: bool = False
    description: Optional[str] = None
    tech_used: Optional[List[str]] = None
    achievements: Optional[List[str]] = None


class EducationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    profile_id: Optional[int] = None
    school: str
    degree: str
    field_of_study: Optional[str] = None
    location: Optional[str] = None
    start_date: str
    end_date: Optional[str] = None
    currently_studying: bool = False
    gpa: Optional[str] = None
    achievements: Optional[List[str]] = None


class EducationCreate(BaseModel):
    school: str
    degree: str
    field_of_study: Optional[str] = None
    location: Optional[str] = None
    start_date: str
    end_date: Optional[str] = None
    currently_studying: bool = False
    gpa: Optional[str] = None
    achievements: Optional[List[str]] = None


class UserProfileCreate(BaseModel):
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    website: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    authorized_to_work_in_us: bool = False
    visa_sponsorship_needed: bool = False
    currently_employed: bool = False
    notice_period_days: Optional[int] = None
    desired_roles: Optional[List[str]] = None
    desired_salary_min: Optional[int] = None
    desired_salary_max: Optional[int] = None
    desired_salary_currency: str = "USD"
    preferred_locations: Optional[List[str]] = None
    remote_only: bool = True
    open_to_relocation: bool = False
    open_to_contract: bool = True
    open_to_fulltime: bool = True
    how_did_you_hear: Optional[str] = None
    cover_letter_intro: Optional[str] = None
    additional_notes: Optional[str] = None
    gender: Optional[str] = None
    hispanic_latino: Optional[str] = None
    veteran_status: Optional[str] = None
    disability_status: Optional[str] = None
    custom_answers: Optional[dict] = None
    experiences: Optional[List[WorkExperienceCreate]] = None
    education: Optional[List[EducationCreate]] = None


class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    website: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    authorized_to_work_in_us: Optional[bool] = None
    visa_sponsorship_needed: Optional[bool] = None
    currently_employed: Optional[bool] = None
    notice_period_days: Optional[int] = None
    desired_roles: Optional[List[str]] = None
    desired_salary_min: Optional[int] = None
    desired_salary_max: Optional[int] = None
    desired_salary_currency: Optional[str] = None
    preferred_locations: Optional[List[str]] = None
    remote_only: Optional[bool] = None
    open_to_relocation: Optional[bool] = None
    open_to_contract: Optional[bool] = None
    open_to_fulltime: Optional[bool] = None
    how_did_you_hear: Optional[str] = None
    cover_letter_intro: Optional[str] = None
    additional_notes: Optional[str] = None
    gender: Optional[str] = None
    hispanic_latino: Optional[str] = None
    veteran_status: Optional[str] = None
    disability_status: Optional[str] = None
    custom_answers: Optional[dict] = None


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    website: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    authorized_to_work_in_us: bool = False
    visa_sponsorship_needed: bool = False
    currently_employed: bool = False
    notice_period_days: Optional[int] = None
    desired_roles: Optional[List[str]] = None
    desired_salary_min: Optional[int] = None
    desired_salary_max: Optional[int] = None
    desired_salary_currency: str = "USD"
    preferred_locations: Optional[List[str]] = None
    remote_only: bool = True
    open_to_relocation: bool = False
    open_to_contract: bool = True
    open_to_fulltime: bool = True
    how_did_you_hear: Optional[str] = None
    cover_letter_intro: Optional[str] = None
    additional_notes: Optional[str] = None
    gender: Optional[str] = None
    hispanic_latino: Optional[str] = None
    veteran_status: Optional[str] = None
    disability_status: Optional[str] = None
    custom_answers: Optional[dict] = None
    experiences: List[WorkExperienceSchema] = []
    education: List[EducationSchema] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
