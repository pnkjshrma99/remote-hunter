from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class JobBase(BaseModel):
    title: str
    company: str
    url: str
    source: str
    description: Optional[str] = None
    location: Optional[str] = None
    salary: Optional[str] = None
    tech_stack: Optional[str] = None
    company_size: Optional[str] = None
    experience_level: Optional[str] = None
    region_eligibility: Optional[str] = None


class JobCreate(JobBase):
    external_id: str
    posted_at: Optional[datetime] = None


class JobUpdate(BaseModel):
    is_applied: Optional[bool] = None
    is_active: Optional[bool] = None


class JobResponse(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    posted_at: Optional[datetime] = None
    scraped_at: datetime
    is_applied: bool
    is_active: bool


class JobFilter(BaseModel):
    search: Optional[str] = None
    source: Optional[str] = None
    tech_stack: Optional[str] = None
    company_size: Optional[str] = None
    experience_level: Optional[str] = None
    region_eligibility: Optional[str] = None
    is_applied: Optional[bool] = None
    is_active: bool = True
    limit: int = Field(default=100, le=500)
    offset: int = 0


class JobStats(BaseModel):
    total_jobs: int
    applied_count: int
    new_today: int
    by_tech_stack: dict
    by_company_size: dict
    by_day: dict
    by_source: dict


class ScrapeRequest(BaseModel):
    query: str = "DevOps Engineer"
    min_experience: Optional[int] = None
    max_experience: Optional[int] = 2
    posted_within_days: Optional[int] = 14
    remote_only: bool = True
    global_or_india: bool = True
    exclude_indian_hq: bool = True
    strict_experience: bool = False
    strict_title: bool = True
    strict_junior: bool = False
    send_alerts: bool = True
    sources: List[str] = Field(default_factory=list)
    linkedin_urls: List[str] = Field(default_factory=list)
