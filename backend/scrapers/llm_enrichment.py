"""LLM enrichment layer for job data.

Uses LLM to extract structured data from unstructured job descriptions.
Runs only after cheap filtering to minimize API costs.
"""

import json
import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from scrapers.schemas import NormalizedJob, SeniorityLevel, JobType, RemoteType
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

LLM_SYSTEM_PROMPT = """You are a structured job-posting extraction engine.

Input:
A raw job title, company name, and full job description.

Task:
Extract the information into strict JSON only. Do not add commentary, markdown, or extra text.

Return this schema:
{
  "title": string | null,
  "company": string | null,
  "location": string | null,
  "remote": boolean | null,
  "job_type": string | null,
  "seniority": string | null,
  "experience_min_years": number | null,
  "experience_max_years": number | null,
  "salary_min": number | null,
  "salary_max": number | null,
  "salary_currency": string | null,
  "skills": string[],
  "responsibilities": string[],
  "keywords": string[],
  "confidence": number
}

Rules:
- Use only the information present in the input.
- Infer carefully from context when the text is explicit enough.
- If something is unclear, use null.
- Prefer conservative extraction over guessing.
- Keep skills and keywords concise.
- confidence must be between 0 and 1.
- Output valid JSON only.

Examples of seniority:
- intern, trainee, apprentice
- junior, entry level, graduate
- mid-level
- senior, staff, principal, lead, manager, director

Examples of job type:
- full-time
- part-time
- contract
- internship
- freelance
- temporary
- unknown"""


class LLMEnricher:
    """Enriches job data using LLM API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.api_key = api_key or getattr(settings, 'llm_api_key', None)
        self.api_base = api_base or getattr(settings, 'llm_api_base', "https://api.openai.com/v1")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.enabled = bool(self.api_key)
        
        if not self.enabled:
            logger.warning("LLM enrichment disabled: no API key configured")
    
    def enrich(self, job: NormalizedJob) -> NormalizedJob:
        """Enrich a job with LLM-extracted data.
        
        Args:
            job: Job to enrich
            
        Returns:
            Enriched job with additional fields
        """
        if not self.enabled:
            logger.debug("LLM enrichment disabled, returning job as-is")
            return job
        
        try:
            extracted = self._call_llm(job)
            if extracted:
                job = self._apply_extraction(job, extracted)
                job.confidence_score = extracted.get("confidence", 0.5)
            else:
                logger.warning(f"LLM extraction failed for job {job.external_id}")
        except Exception as e:
            logger.error(f"LLM enrichment error for job {job.external_id}: {e}")
        
        return job
    
    def enrich_batch(
        self,
        jobs: List[NormalizedJob],
        min_relevance: float = 0.7
    ) -> List[NormalizedJob]:
        """Enrich a batch of jobs, only those above relevance threshold.
        
        Args:
            jobs: Jobs to enrich
            min_relevance: Minimum relevance score to enrich
            
        Returns:
            Enriched jobs
        """
        if not self.enabled:
            logger.debug("LLM enrichment disabled, returning jobs as-is")
            return jobs
        
        # Filter by relevance
        high_relevance_jobs = [j for j in jobs if j.relevance_score >= min_relevance]
        low_relevance_jobs = [j for j in jobs if j.relevance_score < min_relevance]
        
        logger.info(
            f"Enriching {len(high_relevance_jobs)} high-relevance jobs "
            f"(skipping {len(low_relevance_jobs)} low-relevance jobs)"
        )
        
        enriched_jobs = []
        for job in high_relevance_jobs:
            try:
                enriched = self.enrich(job)
                enriched_jobs.append(enriched)
            except Exception as e:
                logger.error(f"Failed to enrich job {job.external_id}: {e}")
                enriched_jobs.append(job)  # Keep original on failure
        
        # Add low-relevance jobs unchanged
        enriched_jobs.extend(low_relevance_jobs)
        
        return enriched_jobs
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _call_llm(self, job: NormalizedJob) -> Optional[Dict[str, Any]]:
        """Call LLM API to extract structured data."""
        user_prompt = f"""Title: {job.title}
Company: {job.company}
Description: {job.description[:4000]}"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,  # Low temperature for consistent extraction
            "max_tokens": 1000
        }
        
        url = f"{self.api_base}/chat/completions"
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # Parse JSON response
                extracted = json.loads(content.strip())
                return extracted
                
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API error: {e.response.status_code}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None
    
    def _apply_extraction(self, job: NormalizedJob, extracted: Dict[str, Any]) -> NormalizedJob:
        """Apply LLM-extracted data to job.
        
        Only overwrites fields if they are currently None/unknown.
        """
        # Seniority
        if extracted.get("seniority"):
            job.seniority = self._parse_seniority(extracted["seniority"])
        
        # Experience
        if extracted.get("experience_min_years") is not None:
            job.experience_min_years = extracted["experience_min_years"]
        if extracted.get("experience_max_years") is not None:
            job.experience_max_years = extracted["experience_max_years"]
        
        # Salary
        if extracted.get("salary_min") is not None:
            job.salary_min = extracted["salary_min"]
        if extracted.get("salary_max") is not None:
            job.salary_max = extracted["salary_max"]
        if extracted.get("salary_currency"):
            job.salary_currency = extracted["salary_currency"]
        
        # Job type
        if extracted.get("job_type"):
            job.job_type = self._parse_job_type(extracted["job_type"])
        
        # Remote
        if extracted.get("remote") is not None:
            job.remote_type = RemoteType.FULLY_REMOTE if extracted["remote"] else RemoteType.ONSITE
        
        # Skills
        if extracted.get("skills"):
            job.skills = extracted["skills"]
        
        # Tags/keywords
        if extracted.get("keywords"):
            job.tags = extracted["keywords"]
        
        # Responsibilities
        if extracted.get("responsibilities"):
            job.responsibilities = extracted["responsibilities"]
        
        # Location
        if extracted.get("location") and not job.location:
            job.location = extracted["location"]
        
        return job
    
    def _parse_seniority(self, seniority_str: str) -> SeniorityLevel:
        """Parse seniority string to enum."""
        seniority_lower = seniority_str.lower()
        
        seniority_map = {
            "intern": SeniorityLevel.INTERN,
            "trainee": SeniorityLevel.INTERN,
            "apprentice": SeniorityLevel.INTERN,
            "junior": SeniorityLevel.JUNIOR,
            "entry level": SeniorityLevel.JUNIOR,
            "graduate": SeniorityLevel.JUNIOR,
            "mid-level": SeniorityLevel.MID_LEVEL,
            "mid level": SeniorityLevel.MID_LEVEL,
            "senior": SeniorityLevel.SENIOR,
            "staff": SeniorityLevel.STAFF,
            "principal": SeniorityLevel.PRINCIPAL,
            "lead": SeniorityLevel.LEAD,
            "manager": SeniorityLevel.MANAGER,
            "director": SeniorityLevel.DIRECTOR,
            "vp": SeniorityLevel.VP,
            "executive": SeniorityLevel.EXECUTIVE,
        }
        
        for key, value in seniority_map.items():
            if key in seniority_lower:
                return value
        
        return SeniorityLevel.UNKNOWN
    
    def _parse_job_type(self, job_type_str: str) -> JobType:
        """Parse job type string to enum."""
        job_type_lower = job_type_str.lower()
        
        job_type_map = {
            "full-time": JobType.FULL_TIME,
            "full time": JobType.FULL_TIME,
            "part-time": JobType.PART_TIME,
            "part time": JobType.PART_TIME,
            "contract": JobType.CONTRACT,
            "internship": JobType.INTERNSHIP,
            "freelance": JobType.FREELANCE,
            "temporary": JobType.TEMPORARY,
        }
        
        for key, value in job_type_map.items():
            if key in job_type_lower:
                return value
        
        return JobType.UNKNOWN


def enrich_jobs_with_llm(
    jobs: List[NormalizedJob],
    min_relevance: float = 0.7,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    model: str = "gpt-3.5-turbo"
) -> List[NormalizedJob]:
    """Convenience function to enrich jobs with LLM.
    
    Args:
        jobs: Jobs to enrich
        min_relevance: Minimum relevance score to enrich
        api_key: LLM API key (optional, uses config if not provided)
        api_base: LLM API base URL (optional, uses config if not provided)
        model: LLM model to use
    
    Returns:
        Enriched jobs
    """
    enricher = LLMEnricher(
        api_key=api_key,
        api_base=api_base,
        model=model
    )
    return enricher.enrich_batch(jobs, min_relevance=min_relevance)
