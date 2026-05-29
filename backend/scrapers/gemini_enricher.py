"""Gemini-powered job enrichment.

Uses Google Gemini API to extract structured data from job descriptions,
classify roles, detect fake jobs, and enrich metadata.
Falls back to rule-based extraction when Gemini API is unavailable.
"""

import json
import logging
import re
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from scrapers.schemas import NormalizedJob, SeniorityLevel, JobType, RemoteType
from app.config import get_settings

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Extract structured job data from the following job posting.
Return ONLY valid JSON with no markdown, no explanation.

Schema:
{
  "title": string | null,
  "company": string | null,
  "location": string | null,
  "remote": boolean | null,
  "job_type": "full-time" | "part-time" | "contract" | "internship" | "freelance" | "temporary" | null,
  "seniority": "intern" | "junior" | "mid-level" | "senior" | "staff" | "principal" | "lead" | "manager" | "director" | "vp" | "executive" | null,
  "experience_min_years": number | null,
  "experience_max_years": number | null,
  "salary_min": number | null,
  "salary_max": number | null,
  "salary_currency": string | null,
  "skills": string[],
  "keywords": string[],
  "role_category": "devops" | "backend" | "frontend" | "fullstack" | "data" | "mobile" | "qa" | "security" | "design" | "product" | "management" | "other",
  "is_fake": boolean,
  "confidence": number
}

Job: {title} at {company}
Description: {description}"""


@dataclass
class GeminiExtraction:
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    remote: Optional[bool] = None
    job_type: Optional[str] = None
    seniority: Optional[str] = None
    experience_min_years: Optional[int] = None
    experience_max_years: Optional[int] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    skills: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    role_category: str = "other"
    is_fake: bool = False
    confidence: float = 0.0


class GeminiEnricher:
    """Enriches job data using Google Gemini API with rule-based fallback."""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.gemini_api_key
        self.model = "gemini-2.0-flash"
        self.enabled = bool(self.api_key)
        self.timeout = 15

        if self.enabled:
            logger.info("Gemini enricher initialized")
        else:
            logger.warning("Gemini enricher disabled: no API key configured")

    def _check_quota(self) -> bool:
        """Quick check if Gemini API is reachable."""
        if not self.enabled:
            return False
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
        try:
            r = httpx.get(url, timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    def _call_gemini(self, prompt: str) -> Optional[Dict[str, Any]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1024,
            },
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(url, json=payload)
                if r.status_code == 429:
                    logger.warning("Gemini quota exceeded")
                    return None
                r.raise_for_status()
                data = r.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
                cleaned = re.sub(r"\s*```$", "", cleaned)
                return json.loads(cleaned)
        except (httpx.HTTPStatusError, httpx.TimeoutException, json.JSONDecodeError,
                KeyError, IndexError) as e:
            logger.debug(f"Gemini API call failed: {e}")
            return None

    def enrich(self, job: NormalizedJob) -> NormalizedJob:
        """Enrich a single job using Gemini, falling back to rule-based."""
        if not self.enabled or not job.description or len(job.description) < 50:
            return self._rule_based_enrich(job)

        prompt = EXTRACTION_PROMPT.format(
            title=job.title,
            company=job.company,
            description=job.description[:4000],
        )

        extracted = self._call_gemini(prompt)
        if extracted:
            try:
                gemini_data = GeminiExtraction(**{k: v for k, v in extracted.items()
                                                   if k in GeminiExtraction.__dataclass_fields__})
                return self._apply_gemini_extraction(job, gemini_data)
            except Exception as e:
                logger.debug(f"Failed to apply Gemini extraction: {e}")

        return self._rule_based_enrich(job)

    def enrich_batch(self, jobs: List[NormalizedJob],
                     min_relevance: float = 0.0) -> List[NormalizedJob]:
        if not self.enabled or not jobs:
            return [self._rule_based_enrich(j) for j in jobs]

        candidates = [j for j in jobs if j.relevance_score >= min_relevance and j.description and len(j.description) >= 50]
        others = [j for j in jobs if j not in candidates]

        logger.info(f"Gemini enriching {len(candidates)}/{len(jobs)} jobs")

        enriched = []
        for job in candidates:
            enriched.append(self.enrich(job))

        enriched.extend(self._rule_based_enrich(j) for j in others)
        return enriched

    def _apply_gemini_extraction(self, job: NormalizedJob, data: GeminiExtraction) -> NormalizedJob:
        if data.seniority:
            job.seniority = self._parse_seniority(data.seniority)
        if data.experience_min_years is not None:
            job.experience_min_years = data.experience_min_years
        if data.experience_max_years is not None:
            job.experience_max_years = data.experience_max_years
        if data.salary_min is not None:
            job.salary_min = data.salary_min
        if data.salary_max is not None:
            job.salary_max = data.salary_max
        if data.salary_currency:
            job.salary_currency = data.salary_currency
        if data.job_type:
            job.job_type = self._parse_job_type(data.job_type)
        if data.remote is not None:
            job.remote_type = RemoteType.FULLY_REMOTE if data.remote else RemoteType.ONSITE
        if data.skills:
            job.skills = data.skills
        if data.keywords:
            job.tags = data.keywords
        if data.location and not job.location:
            job.location = data.location
        if data.is_fake:
            job.is_likely_fake = True
        if data.confidence:
            job.confidence_score = data.confidence
        return job

    def _rule_based_enrich(self, job: NormalizedJob) -> NormalizedJob:
        """Rule-based enrichment fallback when Gemini is unavailable."""
        combined = f"{job.title} {job.description or ''} {job.location or ''}".lower()

        # Seniority detection
        if job.seniority == SeniorityLevel.UNKNOWN:
            seniority_patterns = [
                (SeniorityLevel.INTERN, r"\bintern\b|\btrainee\b|\bapprentice\b"),
                (SeniorityLevel.JUNIOR, r"\bjunior\b|\bentry[\s-]?level\b|\bgraduate\b|\bnew grad\b"),
                (SeniorityLevel.SENIOR, r"\bsenior\b|\bsr\.?\b|staff|\bprincipal\b"),
                (SeniorityLevel.LEAD, r"\blead\b|\bhead of\b"),
                (SeniorityLevel.MANAGER, r"\bmanager\b"),
                (SeniorityLevel.DIRECTOR, r"\bdirector\b"),
                (SeniorityLevel.VP, r"\bvp\b|\bvice president\b"),
                (SeniorityLevel.EXECUTIVE, r"\bexecutive\b|\bcto\b|\bceo\b|\bcfo\b"),
            ]
            for level, pattern in seniority_patterns:
                if re.search(pattern, combined, re.I):
                    job.seniority = level
                    break

        # Remote detection
        if job.remote_type == RemoteType.UNKNOWN:
            if re.search(r"\bremote\b|\bworldwide\b|\banywhere\b|\bglobal\b", combined, re.I):
                job.remote_type = RemoteType.FULLY_REMOTE
            elif re.search(r"\bhybrid\b", combined, re.I):
                job.remote_type = RemoteType.HYBRID

        # Experience extraction from description
        if job.experience_min_years is None and job.description:
            exp = self._extract_exp_years(job.description)
            if exp:
                job.experience_min_years, job.experience_max_years = exp

        # Fake job detection
        if not job.is_likely_fake:
            fake_signals = [
                r"earn \$?\d+k?/?(day|week)",
                r"no experience needed.*(?:high|great) pay",
                r"work from home.*\$?\d+k",
                r"click here to apply",
                r"apply.*now.*limited",
                r"bit\.ly|tinyurl|shortlink",
                r"make money fast",
                r"immediate start.*no experience",
                r"unlimited earning potential",
                r"be your own boss",
                r"copy and paste",
            ]
            signal_count = 0
            for pattern in fake_signals:
                if re.search(pattern, combined, re.I):
                    signal_count += 1
            if signal_count >= 2:
                job.is_likely_fake = True
                job.confidence_score = min(job.confidence_score, 0.3)

        return job

    def _parse_seniority(self, value: str) -> SeniorityLevel:
        mapping = {
            "intern": SeniorityLevel.INTERN, "trainee": SeniorityLevel.INTERN,
            "junior": SeniorityLevel.JUNIOR, "entry level": SeniorityLevel.JUNIOR,
            "mid-level": SeniorityLevel.MID_LEVEL, "mid": SeniorityLevel.MID_LEVEL,
            "senior": SeniorityLevel.SENIOR, "staff": SeniorityLevel.STAFF,
            "principal": SeniorityLevel.PRINCIPAL, "lead": SeniorityLevel.LEAD,
            "manager": SeniorityLevel.MANAGER, "director": SeniorityLevel.DIRECTOR,
            "vp": SeniorityLevel.VP, "executive": SeniorityLevel.EXECUTIVE,
        }
        return mapping.get(value.lower().strip(), SeniorityLevel.UNKNOWN)

    def _parse_job_type(self, value: str) -> JobType:
        mapping = {
            "full-time": JobType.FULL_TIME, "full time": JobType.FULL_TIME,
            "part-time": JobType.PART_TIME, "part time": JobType.PART_TIME,
            "contract": JobType.CONTRACT,
            "internship": JobType.INTERNSHIP,
            "freelance": JobType.FREELANCE,
            "temporary": JobType.TEMPORARY,
        }
        return mapping.get(value.lower().strip(), JobType.UNKNOWN)

    def _extract_exp_years(self, text: str) -> Optional[Tuple[int, Optional[int]]]:
        range_m = re.search(r"(\d{1,2})\s*[-–to]+\s*(\d{1,2})\s*(?:years?|yrs?)", text, re.I)
        if range_m:
            return (int(range_m.group(1)), int(range_m.group(2)))
        plus_m = re.search(r"(\d{1,2})\s*\+\s*(?:years?|yrs?)", text, re.I)
        if plus_m:
            return (int(plus_m.group(1)), None)
        return None
