"""Relevance scoring system for job matching.

Replaces binary pass/fail logic with a numeric score from 0 to 1.
Score considers title match, description match, seniority match, 
experience match, remote/location match, freshness, and dedupe confidence.
"""

import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from difflib import SequenceMatcher

from scrapers.schemas import NormalizedJob, SearchCriteria, SeniorityLevel, RemoteType
from scrapers.filters import _infer_role_category, is_relevant_role

logger = logging.getLogger(__name__)


class JobScorer:
    """Calculates relevance scores for jobs against search criteria."""
    
    def __init__(self, criteria: SearchCriteria):
        self.criteria = criteria
    
    def calculate_score(self, job: NormalizedJob) -> float:
        """Calculate overall relevance score (0-1).
        
        Score components:
        - Title match: 0-0.3
        - Description match: 0-0.25
        - Experience match: 0-0.2
        - Seniority match: 0-0.1
        - Remote/location match: 0-0.1
        - Freshness: 0-0.05
        - Quality: 0-0.1 (completeness bonus)
        
        The quality score acts as a tiebreaker — it doesn't replace
        relevance but ensures that among similarly relevant jobs,
        the ones with richer listings rank higher.
        """
        title_score = self._score_title_match(job)
        desc_score = self._score_description_match(job)
        exp_score = self._score_experience_match(job)
        seniority_score = self._score_seniority_match(job)
        location_score = self._score_location_match(job)
        freshness_score = self._score_freshness(job)
        quality_score = self._score_quality(job)
        
        total = (
            title_score * 0.3 +
            desc_score * 0.25 +
            exp_score * 0.2 +
            seniority_score * 0.1 +
            location_score * 0.1 +
            freshness_score * 0.05 +
            quality_score * 0.1  # Bonus for listing completeness
        )
        
        return round(min(1.0, max(0.0, total)), 3)
    
    def _score_title_match(self, job: NormalizedJob) -> float:
        """Score title match (0-1) with multi-level semantic matching.
        
        Levels:
        1.0 - Exact match
        0.8 - Same role category (e.g. 'devops' query matching 'SRE' job)
        0.6 - All query terms present in title
        0.4 - Partial query terms in title
        0.2 - Only role category match (no direct term hit)
        0.0 - No match at all
        """
        if not self.criteria.query:
            return 0.5  # Neutral if no query
        
        query_lower = self.criteria.query.lower()
        title_lower = job.title.lower()
        
        # Level 1: Exact match
        if query_lower == title_lower:
            return 1.0
        
        # Query terms in title
        terms = self.criteria.query_terms
        if not terms:
            return 0.5
        
        title_hits = sum(1 for term in terms if term in title_lower)
        
        if title_hits > 0:
            # Partial match based on term coverage
            coverage = title_hits / len(terms)
            
            # Boost if all terms present
            if coverage == 1.0:
                return 1.0
            
            # Penalize if strict_title and not all terms present
            if self.criteria.strict_title and coverage < 1.0:
                return coverage * 0.5
            
            return coverage
        
        # Level 2: No direct term hits - check role category match
        # e.g. query "DevOps Engineer" matches job title "Site Reliability Engineer"
        job_category = _infer_role_category(job.title, job.description)
        if job_category:
            query_category = _infer_role_category(query_lower, query_lower)
            if query_category and job_category == query_category:
                return 0.8  # Same role category - strong partial credit
        
        # Level 3: No match at all
        return 0.0
    
    def _score_description_match(self, job: NormalizedJob) -> float:
        """Score description match (0-1)."""
        if not self.criteria.query or not job.description:
            return 0.5  # Neutral if no query or description
        
        terms = self.criteria.query_terms
        if not terms:
            return 0.5
        
        desc_lower = job.description.lower()
        combined = f"{job.title} {job.description}".lower()
        
        # Count term matches in description
        desc_hits = sum(1 for term in terms if term in desc_lower)
        combined_hits = sum(1 for term in terms if term in combined)
        
        if combined_hits == 0:
            return 0.0
        
        # Score based on combined matches (title + description)
        coverage = combined_hits / len(terms)
        
        # If strict_title is False, allow description-only matches
        if not self.criteria.strict_title:
            return min(1.0, coverage + 0.2)  # Boost for flexible matching
        
        return coverage
    
    def _score_experience_match(self, job: NormalizedJob) -> float:
        """Score experience match (0-1)."""
        if self.criteria.min_experience is None and self.criteria.max_experience is None:
            return 1.0  # No experience filter
        
        job_min = job.experience_min_years or 0
        job_max = job.experience_max_years or 99
        
        desired_min = self.criteria.min_experience or 0
        desired_max = self.criteria.max_experience or 99
        
        # Check for overlap
        if job_min <= desired_max and job_max >= desired_min:
            # Calculate overlap score
            overlap_start = max(job_min, desired_min)
            overlap_end = min(job_max, desired_max)
            overlap_range = overlap_end - overlap_start
            
            job_range = job_max - job_min if job_max != job_min else 1
            desired_range = desired_max - desired_min if desired_max != desired_min else 1
            
            # Score based on overlap proportion
            overlap_score = overlap_range / max(job_range, desired_range)
            
            # Perfect match if job range is within desired range
            if job_min >= desired_min and job_max <= desired_max:
                return 1.0
            
            return min(1.0, overlap_score + 0.3)
        
        # No overlap
        if self.criteria.strict_experience:
            return 0.0
        
        # Partial credit for close ranges
        if job_min <= desired_max + 1 and job_max >= desired_min - 1:
            return 0.3
        
        return 0.0
    
    def _score_seniority_match(self, job: NormalizedJob) -> float:
        """Score seniority match (0-1)."""
        if not self.criteria.seniority_levels:
            return 1.0  # No seniority filter
        
        if job.seniority == SeniorityLevel.UNKNOWN:
            return 0.5  # Neutral if unknown
        
        # Exact match
        if job.seniority in self.criteria.seniority_levels:
            return 1.0
        
        # Seniority hierarchy for partial matches
        hierarchy = {
            SeniorityLevel.INTERN: 0,
            SeniorityLevel.JUNIOR: 1,
            SeniorityLevel.MID_LEVEL: 2,
            SeniorityLevel.SENIOR: 3,
            SeniorityLevel.STAFF: 4,
            SeniorityLevel.PRINCIPAL: 5,
            SeniorityLevel.LEAD: 5,
            SeniorityLevel.MANAGER: 6,
            SeniorityLevel.DIRECTOR: 7,
            SeniorityLevel.VP: 8,
            SeniorityLevel.EXECUTIVE: 9,
        }
        
        job_level = hierarchy.get(job.seniority, 2)
        
        # Find closest match in desired levels
        closest_diff = min(
            abs(job_level - hierarchy.get(s, 2))
            for s in self.criteria.seniority_levels
        )
        
        # Score decreases with distance from desired level
        if closest_diff == 0:
            return 1.0
        elif closest_diff == 1:
            return 0.7
        elif closest_diff == 2:
            return 0.4
        else:
            return 0.1
    
    def _score_location_match(self, job: NormalizedJob) -> float:
        """Score remote/location match (0-1)."""
        if not self.criteria.remote_only:
            return 1.0  # No remote filter
        
        # Fully remote
        if job.remote_type == RemoteType.FULLY_REMOTE:
            return 1.0
        
        # Hybrid - partial credit
        if job.remote_type == RemoteType.HYBRID:
            return 0.5
        
        # Onsite - no credit
        if job.remote_type == RemoteType.ONSITE:
            return 0.0
        
        # Unknown - check location text
        if job.remote_type == RemoteType.UNKNOWN:
            location_lower = (job.location or "").lower()
            desc_lower = (job.description or "").lower()
            combined = f"{location_lower} {desc_lower}"
            
            # Check for remote indicators
            remote_indicators = ["remote", "worldwide", "anywhere", "global"]
            if any(indicator in combined for indicator in remote_indicators):
                return 0.8
            
            # Check for onsite indicators
            onsite_indicators = ["onsite", "on-site", "in office", "hybrid"]
            if any(indicator in combined for indicator in onsite_indicators):
                return 0.3
            
            return 0.5  # Neutral if unknown
        
        return 0.5
    
    def _score_quality(self, job: NormalizedJob) -> float:
        """Score listing completeness/quality (0-1).
        
        Rewards jobs with richer metadata so that among equally relevant
        results, the ones with more details rank higher.
        
        Quality signals (weighted):
        - Has description >= 200 chars: 0.20
        - Has description >= 100 chars: 0.10
        - Has salary_min and salary_max: 0.20
        - Has at least one skill: 0.15
        - Has skills list (multiple): 0.10
        - Has requirements list: 0.10
        - Has responsibilities list: 0.10
        - Has tech stack in tags: 0.05
        - Has a location: 0.05
        - Has seniority inferred: 0.05
        """
        score = 0.0
        
        # Description length & quality
        desc = job.description or ""
        if len(desc) >= 500:
            score += 0.20  # Rich, detailed description
        elif len(desc) >= 200:
            score += 0.15  # Good description
        elif len(desc) >= 100:
            score += 0.10  # Short description
        elif len(desc) >= 50:
            score += 0.05  # Minimal description
        else:
            score += 0.0   # No description
            
        # Salary info — strongest signal of listing quality
        if job.salary_min is not None and job.salary_max is not None:
            if job.salary_max - job.salary_min > 0:
                score += 0.25  # Real salary range
            else:
                score += 0.15  # Single salary value
        elif job.salary_min is not None or job.salary_max is not None:
            score += 0.10  # Partial salary info
        
        # Skills & tech stack
        if job.skills and len(job.skills) >= 3:
            score += 0.20  # Rich skills list
        elif job.skills and len(job.skills) >= 1:
            score += 0.12  # Has some skills
        elif job.tags and len(job.tags) >= 1:
            score += 0.05  # Has tags but no explicit skills
        
        # Requirements & responsibilities — structured listing
        if job.requirements and len(job.requirements) >= 2:
            score += 0.10  # Structured requirements
        elif job.requirements and len(job.requirements) == 1:
            score += 0.05  # Single requirement
            
        if job.responsibilities and len(job.responsibilities) >= 2:
            score += 0.10  # Structured responsibilities
        elif job.responsibilities and len(job.responsibilities) == 1:
            score += 0.05  # Single responsibility
        
        # Location
        if job.location and len(job.location.strip()) > 0:
            score += 0.05
        
        # Seniority inference
        if job.seniority != SeniorityLevel.UNKNOWN:
            score += 0.05
        
        # Clamp to 1.0
        return round(min(1.0, score), 2)
    
    def _score_freshness(self, job: NormalizedJob) -> float:
        """Score job freshness (0-1)."""
        if not job.posted_at or not self.criteria.posted_within_days:
            return 1.0  # No freshness filter
        
        # Handle string datetime (defensive)
        if isinstance(job.posted_at, str):
            from scrapers.filters import _parse_datetime
            posted = _parse_datetime(job.posted_at)
            if not posted:
                return 1.0  # Failed to parse, treat as neutral
        else:
            posted = job.posted_at
        
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        posted = posted.replace(tzinfo=None) if posted.tzinfo else posted
        days_old = (now - posted).days
        
        max_days = self.criteria.posted_within_days
        
        if days_old <= 0:
            return 1.0  # Posted today
        
        if days_old <= max_days:
            # Linear decay from 1.0 to 0.5 over the period
            return 1.0 - (days_old / max_days) * 0.5
        
        # Older than max days
        if days_old <= max_days * 2:
            return 0.3
        
        return 0.0


def calculate_relevance_score(job: NormalizedJob, criteria: SearchCriteria) -> float:
    """Convenience function to calculate relevance score."""
    scorer = JobScorer(criteria)
    return scorer.calculate_score(job)


def filter_by_relevance(
    jobs: List[NormalizedJob],
    criteria: SearchCriteria,
    min_score: float = 0.5,
    max_results: Optional[int] = None
) -> List[NormalizedJob]:
    """Filter jobs by relevance score and return sorted results.
    
    Args:
        jobs: List of normalized jobs
        criteria: Search criteria
        min_score: Minimum relevance score (0-1)
        max_results: Maximum number of results to return
    
    Returns:
        Sorted list of jobs with relevance >= min_score
    """
    scorer = JobScorer(criteria)
    
    # Calculate scores
    scored_jobs = []
    for job in jobs:
        score = scorer.calculate_score(job)
        job.relevance_score = score
        if score >= min_score:
            scored_jobs.append(job)
    
    # Sort by relevance score (descending)
    scored_jobs.sort(key=lambda j: j.relevance_score, reverse=True)
    
    # Limit results
    if max_results:
        scored_jobs = scored_jobs[:max_results]
    
    logger.info(
        f"Filtered {len(jobs)} jobs -> {len(scored_jobs)} with score >= {min_score}"
    )
    
    return scored_jobs
