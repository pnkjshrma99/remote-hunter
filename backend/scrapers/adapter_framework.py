"""Enhanced Source Adapter Framework

Provides modular, extensible architecture for job source integrations.
Each source adapter implements a standard interface for consistent behavior.
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)


class SourceType(str, Enum):
    """Type of source"""
    API = "api"
    GRAPHQL = "graphql"
    RSS = "rss"
    WEB_SCRAPE = "web_scrape"
    ATS = "ats"


@dataclass
class SourceConfig:
    """Configuration for a source"""
    name: str
    source_type: SourceType
    api_endpoint: Optional[str] = None
    trust_score: float = 5.0  # 0-10
    priority: int = 5  # 1-10, higher = more priority
    rate_limit_per_hour: int = 1000
    retry_strategy: Dict[str, Any] = field(default_factory=lambda: {
        "max_retries": 3,
        "backoff_factor": 1.5,
        "timeout_seconds": 30
    })
    custom_config: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


@dataclass
class IngestionResult:
    """Result from a single ingestion run"""
    source_name: str
    jobs_fetched: int
    jobs_normalized: int
    jobs_valid: int
    jobs_spam: int
    jobs_duplicates: int
    jobs_new: int
    duration_seconds: float
    status: str  # 'success', 'partial', 'failed'
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class SourceAdapter(ABC):
    """
    Abstract base class for all job source adapters.

    Subclasses must implement:
    - fetch_jobs()
    - normalize_job()
    - validate_job()

    Optional overrides:
    - detect_spam()
    - enrich_job()
    - get_source_name()
    """

    def __init__(self, config: SourceConfig):
        self.config = config
        self.logger = logging.getLogger(f"source.{config.name}")
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        """Return source name"""
        return self.config.name

    @property
    def trust_score(self) -> float:
        """Return trust score for this source"""
        return self.config.trust_score

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Clean up resources"""
        if self._session and not self._session.closed:
            await self._session.close()

    @abstractmethod
    async def fetch_jobs(self, criteria: Optional[SearchCriteria] = None) -> List[RawJob]:
        """
        Fetch jobs from source.

        Args:
            criteria: Search criteria to filter/scope results

        Returns:
            List of raw job objects
        """
        pass

    def normalize_job(self, raw: RawJob) -> RawJob:
        """
        Normalize job data to standard format.

        Can be overridden by subclasses for source-specific normalization.
        """
        # Default: minimal normalization
        return raw

    def validate_job(self, job: RawJob) -> bool:
        """
        Validate job has required fields.

        Returns True if job is valid, False otherwise.
        """
        required_fields = ['title', 'company', 'url']
        return all(getattr(job, field, None) for field in required_fields)

    def detect_spam(self, job: RawJob) -> float:
        """
        Detect if job is spam (0-1, where 1 = definitely spam).

        Default implementation checks for obvious spam patterns.
        """
        spam_score = 0.0

        # Check title for spam patterns
        title_lower = job.title.lower() if job.title else ""
        spam_patterns = [
            'bitcoin', 'crypto', 'forex', 'mlm', 'pyramid',
            'guarantee', 'no experience needed'
        ]

        for pattern in spam_patterns:
            if pattern in title_lower:
                spam_score += 0.25

        # Check description
        desc_lower = (job.description or "").lower()
        for pattern in spam_patterns:
            if pattern in desc_lower:
                spam_score += 0.15

        return min(1.0, spam_score)

    def enrich_job(self, job: RawJob) -> RawJob:
        """
        Enrich job with additional metadata.

        Default: no enrichment. Subclasses can override.
        """
        return job

    async def ingest(self, criteria: Optional[SearchCriteria] = None) -> IngestionResult:
        """
        Run complete ingestion pipeline: fetch → normalize → validate → enrich.

        Returns:
            IngestionResult with summary of operation
        """
        start_time = datetime.utcnow()
        result = IngestionResult(
            source_name=self.name,
            jobs_fetched=0,
            jobs_normalized=0,
            jobs_valid=0,
            jobs_spam=0,
            jobs_duplicates=0,
            jobs_new=0,
            duration_seconds=0,
            status='success'
        )

        try:
            # 1. Fetch
            self.logger.info(f"Fetching jobs from {self.name}")
            raw_jobs = await self.fetch_jobs(criteria)
            result.jobs_fetched = len(raw_jobs)
            self.logger.info(f"Fetched {result.jobs_fetched} jobs")

            # 2. Normalize
            normalized_jobs = []
            for raw in raw_jobs:
                try:
                    normalized = self.normalize_job(raw)
                    normalized_jobs.append(normalized)
                except Exception as e:
                    self.logger.warning(f"Failed to normalize job: {e}")
                    continue

            result.jobs_normalized = len(normalized_jobs)

            # 3. Validate
            valid_jobs = []
            for job in normalized_jobs:
                if self.validate_job(job):
                    valid_jobs.append(job)

            result.jobs_valid = len(valid_jobs)

            # 4. Spam detection
            spam_jobs = []
            clean_jobs = []
            for job in valid_jobs:
                spam_score = self.detect_spam(job)
                if spam_score > 0.5:  # Threshold for spam
                    spam_jobs.append(job)
                else:
                    clean_jobs.append(job)

            result.jobs_spam = len(spam_jobs)

            # 5. Enrich
            enriched_jobs = []
            for job in clean_jobs:
                try:
                    enriched = self.enrich_job(job)
                    enriched_jobs.append(enriched)
                except Exception as e:
                    self.logger.warning(f"Failed to enrich job: {e}")
                    enriched_jobs.append(job)

            # 6. Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()
            result.duration_seconds = duration
            result.jobs_new = len(enriched_jobs)

            self.logger.info(
                f"Ingestion complete: {result.jobs_new} jobs "
                f"({result.jobs_spam} spam, {result.jobs_fetched - result.jobs_normalized} failed normalize)"
            )

        except Exception as e:
            self.logger.error(f"Ingestion failed: {e}", exc_info=True)
            result.status = 'failed'
            result.error = str(e)
            duration = (datetime.utcnow() - start_time).total_seconds()
            result.duration_seconds = duration

        return result

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _fetch_json(self, url: str, **kwargs) -> Dict[str, Any]:
        """Fetch JSON with retry logic"""
        session = await self.get_session()
        timeout = aiohttp.ClientTimeout(seconds=self.config.retry_strategy.get('timeout_seconds', 30))

        async with session.get(url, timeout=timeout, **kwargs) as response:
            response.raise_for_status()
            return await response.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _fetch_text(self, url: str, **kwargs) -> str:
        """Fetch text with retry logic"""
        session = await self.get_session()
        timeout = aiohttp.ClientTimeout(seconds=self.config.retry_strategy.get('timeout_seconds', 30))

        async with session.get(url, timeout=timeout, **kwargs) as response:
            response.raise_for_status()
            return await response.text()


# ==============================================================================
# EXAMPLE IMPLEMENTATIONS
# ==============================================================================

class GitHubJobsAdapter(SourceAdapter):
    """GitHub Jobs API adapter"""

    def __init__(self):
        super().__init__(SourceConfig(
            name='github_jobs',
            source_type=SourceType.API,
            api_endpoint='https://jobs.github.com/positions.json',
            trust_score=9.0,
            priority=10
        ))

    async def fetch_jobs(self, criteria: Optional[SearchCriteria] = None) -> List[RawJob]:
        """Fetch from GitHub Jobs API"""
        jobs = []

        params = {
            'full_time': 'true',
            'location': 'remote'
        }

        if criteria and criteria.query:
            params['description'] = criteria.query

        try:
            data = await self._fetch_json(self.config.api_endpoint, params=params)

            for item in data:
                job = RawJob(
                    external_id=self._make_external_id(item['url']),
                    source=self.name,
                    title=item.get('title', ''),
                    company=item.get('company', ''),
                    url=item.get('url', ''),
                    description=item.get('description', ''),
                    location=item.get('location', 'Remote'),
                    salary='',
                    posted_at=item.get('created_at', '')
                )
                jobs.append(job)

        except Exception as e:
            self.logger.error(f"Failed to fetch GitHub Jobs: {e}")

        return jobs

    def _make_external_id(self, url: str) -> str:
        """Generate external ID from URL"""
        import hashlib
        return f"github_{hashlib.md5(url.encode()).hexdigest()[:12]}"


class DevToJobsAdapter(SourceAdapter):
    """Dev.to Jobs API adapter"""

    def __init__(self):
        super().__init__(SourceConfig(
            name='devto_jobs',
            source_type=SourceType.API,
            api_endpoint='https://dev.to/api/listings',
            trust_score=9.0,
            priority=10
        ))

    async def fetch_jobs(self, criteria: Optional[SearchCriteria] = None) -> List[RawJob]:
        """Fetch from Dev.to Jobs API"""
        jobs = []

        params = {
            'category': 'jobs',
            'tag': 'remote'
        }

        try:
            data = await self._fetch_json(self.config.api_endpoint, params=params)

            for item in data:
                job = RawJob(
                    external_id=f"devto_{item.get('id')}",
                    source=self.name,
                    title=item.get('title', ''),
                    company=item.get('company_name', ''),
                    url=item.get('url', ''),
                    description=item.get('description', ''),
                    location=item.get('location', 'Remote'),
                    salary=item.get('tag_list', ''),
                    posted_at=item.get('created_at', '')
                )
                jobs.append(job)

        except Exception as e:
            self.logger.error(f"Failed to fetch Dev.to Jobs: {e}")

        return jobs


# ==============================================================================
# ADAPTER REGISTRY
# ==============================================================================

class SourceRegistry:
    """Registry for managing source adapters"""

    def __init__(self):
        self._adapters: Dict[str, SourceAdapter] = {}

    def register(self, adapter: SourceAdapter) -> None:
        """Register a source adapter"""
        self._adapters[adapter.name] = adapter
        logger.info(f"Registered adapter: {adapter.name}")

    def get(self, name: str) -> Optional[SourceAdapter]:
        """Get adapter by name"""
        return self._adapters.get(name)

    def list_adapters(self) -> List[SourceAdapter]:
        """List all registered adapters"""
        return list(self._adapters.values())

    def list_active(self) -> List[SourceAdapter]:
        """List active adapters"""
        return [a for a in self._adapters.values() if a.config.is_active]

    async def ingest_all(self, criteria: Optional[SearchCriteria] = None) -> Dict[str, IngestionResult]:
        """Run ingestion for all active adapters"""
        results = {}

        tasks = [
            adapter.ingest(criteria)
            for adapter in self.list_active()
        ]

        ingestion_results = await asyncio.gather(*tasks, return_exceptions=True)

        for adapter, result in zip(self.list_active(), ingestion_results):
            if isinstance(result, Exception):
                results[adapter.name] = IngestionResult(
                    source_name=adapter.name,
                    jobs_fetched=0,
                    jobs_normalized=0,
                    jobs_valid=0,
                    jobs_spam=0,
                    jobs_duplicates=0,
                    jobs_new=0,
                    duration_seconds=0,
                    status='failed',
                    error=str(result)
                )
            else:
                results[adapter.name] = result

        return results

    async def close_all(self) -> None:
        """Close all adapters"""
        for adapter in self._adapters.values():
            await adapter.close()


# Global registry instance
_source_registry = SourceRegistry()


def get_source_registry() -> SourceRegistry:
    """Get global source registry"""
    return _source_registry
