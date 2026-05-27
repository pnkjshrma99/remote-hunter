"""Normalized job schema for all scrapers.

This schema provides a unified structure for job data across all sources,
with rich metadata for filtering, scoring, and enrichment.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from enum import Enum


class SeniorityLevel(str, Enum):
    """Standardized seniority levels."""
    INTERN = "intern"
    JUNIOR = "junior"
    MID_LEVEL = "mid_level"
    SENIOR = "senior"
    STAFF = "staff"
    PRINCIPAL = "principal"
    LEAD = "lead"
    MANAGER = "manager"
    DIRECTOR = "director"
    VP = "vp"
    EXECUTIVE = "executive"
    UNKNOWN = "unknown"


class JobType(str, Enum):
    """Standardized job types."""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"
    TEMPORARY = "temporary"
    UNKNOWN = "unknown"


class RemoteType(str, Enum):
    """Remote work types."""
    FULLY_REMOTE = "fully_remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


@dataclass
class NormalizedJob:
    """Normalized job schema used by all sources.
    
    This schema provides a unified structure for job data with rich metadata
    for filtering, scoring, and enrichment.
    """
    # Core identifiers
    external_id: str
    source: str
    title: str
    company: str
    url: str
    
    # Job details
    description: str = ""
    location: str = ""
    remote_type: RemoteType = RemoteType.UNKNOWN
    job_type: JobType = JobType.UNKNOWN
    
    # Experience & seniority
    seniority: SeniorityLevel = SeniorityLevel.UNKNOWN
    experience_min_years: Optional[int] = None
    experience_max_years: Optional[int] = None
    
    # Compensation
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = "USD"
    salary_period: str = "yearly"  # yearly, monthly, hourly
    
    # Skills & requirements
    skills: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    responsibilities: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    
    # Metadata
    posted_at: Optional[datetime] = None
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    
    # Raw data for debugging/fallback
    raw_payload: Dict[str, Any] = field(default_factory=dict)
    
    # Scoring & quality (filled by pipeline)
    relevance_score: float = 0.0
    confidence_score: float = 0.0
    is_likely_fake: bool = False
    is_duplicate: bool = False
    duplicate_group_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "external_id": self.external_id,
            "source": self.source,
            "title": self.title,
            "company": self.company,
            "url": self.url,
            "description": self.description,
            "location": self.location,
            "remote_type": self.remote_type.value,
            "job_type": self.job_type.value,
            "seniority": self.seniority.value,
            "experience_min_years": self.experience_min_years,
            "experience_max_years": self.experience_max_years,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_currency": self.salary_currency,
            "salary_period": self.salary_period,
            "skills": self.skills,
            "tags": self.tags,
            "responsibilities": self.responsibilities,
            "requirements": self.requirements,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "scraped_at": self.scraped_at.isoformat(),
            "relevance_score": self.relevance_score,
            "confidence_score": self.confidence_score,
            "is_likely_fake": self.is_likely_fake,
            "is_duplicate": self.is_duplicate,
            "duplicate_group_id": self.duplicate_group_id,
        }
    
    @classmethod
    def from_raw_job(cls, raw_job: "RawJob") -> "NormalizedJob":
        """Convert from legacy RawJob to NormalizedJob.
        
        This provides backward compatibility with existing scrapers.
        """
        from scrapers.filters import (
            infer_experience_level,
            infer_region_eligibility,
            extract_tech_stack,
            _parse_datetime,
        )
        
        # Infer seniority from experience level string
        seniority_map = {
            "Intern": SeniorityLevel.INTERN,
            "Junior (0-2 years)": SeniorityLevel.JUNIOR,
            "Mid-level": SeniorityLevel.MID_LEVEL,
            "Senior (excluded)": SeniorityLevel.SENIOR,
        }
        exp_level = infer_experience_level(raw_job.title, raw_job.description)
        seniority = seniority_map.get(exp_level, SeniorityLevel.UNKNOWN)
        
        # Extract skills
        combined = f"{raw_job.title} {raw_job.description} {raw_job.location}"
        skills = extract_tech_stack(combined)
        
        # Parse posted_at from string to datetime
        posted_at = _parse_datetime(raw_job.posted_at)
        
        return cls(
            external_id=raw_job.external_id,
            source=raw_job.source,
            title=raw_job.title,
            company=raw_job.company,
            url=raw_job.url,
            description=raw_job.description or "",
            location=raw_job.location or "",
            skills=skills,
            posted_at=posted_at,
            raw_payload={
                "salary": raw_job.salary,
            },
        )


@dataclass
class SearchCriteria:
    """Search criteria with support for source-side filtering."""
    query: str = "DevOps Engineer"
    job_profile_id: Optional[str] = None
    
    # Experience filters
    min_experience: Optional[int] = None
    max_experience: Optional[int] = None
    
    # Location filters
    remote_only: bool = True
    global_or_india: bool = True
    location: Optional[str] = None
    
    # Time filters
    posted_within_days: Optional[int] = 14
    
    # Company filters
    exclude_indian_hq: bool = True
    company_size: Optional[str] = None
    
    # Seniority filter
    seniority_levels: List[SeniorityLevel] = field(default_factory=list)
    
    # Job type filter
    job_types: List[JobType] = field(default_factory=list)
    
    # Strictness
    strict_experience: bool = False
    strict_title: bool = False
    
    # Source-specific
    linkedin_urls: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    
    # LLM enrichment
    enable_llm_enrichment: bool = True
    llm_enrichment_threshold: float = 0.7  # Only enrich jobs with relevance >= threshold
    
    @property
    def query_terms(self) -> List[str]:
        """Extract query terms for matching."""
        terms = re.findall(r"[a-zA-Z0-9+#.]+", self.query.lower())
        stop_words = {"engineer", "developer", "remote", "job", "jobs", "role", "roles"}
        return [term for term in terms if term not in stop_words]
    
    @property
    def role_category(self) -> Optional[str]:
        """Infer the role category from the query for multi-level matching.
        
        Maps queries like 'DevOps Engineer' to a role category like 'devops',
        which can then find related roles like SRE, Platform Engineer, etc.
        """
        query_lower = self.query.lower()
        
        # Direct role category matches
        role_map = {
            "devops": "devops",
            "sre": "devops",
            "site reliability": "devops",
            "platform engineer": "devops",
            "infrastructure": "devops",
            "cloud engineer": "devops",
            "backend": "backend",
            "back-end": "backend",
            "back end": "backend",
            "frontend": "frontend",
            "front-end": "frontend",
            "front end": "frontend",
            "full stack": "fullstack",
            "fullstack": "fullstack",
            "full-stack": "fullstack",
            "data": "data",
            "data science": "data",
            "ml": "data",
            "machine learning": "data",
            "ai": "data",
            "mobile": "mobile",
            "ios": "mobile",
            "android": "mobile",
            "security": "security",
            "qa": "qa",
            "quality assurance": "qa",
            "test": "qa",
        }
        for phrase, category in role_map.items():
            if phrase in query_lower:
                return category
        return None
    
    def to_source_params(self) -> Dict[str, Any]:
        """Convert to source-specific query parameters.
        
        This allows scrapers to apply filtering at the source instead of
        fetching everything and filtering post-fetch.
        """
        params = {}
        
        if self.query:
            params["query"] = self.query
        
        if self.location:
            params["location"] = self.location
        
        if self.remote_only:
            params["remote"] = True
        
        if self.min_experience is not None:
            params["experience_min"] = self.min_experience
        
        if self.max_experience is not None:
            params["experience_max"] = self.max_experience
        
        if self.posted_within_days:
            params["posted_within_days"] = self.posted_within_days
        
        return params
