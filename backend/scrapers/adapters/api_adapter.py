"""API adapter with source-side filtering support.

This adapter provides a base for REST API scrapers with built-in
source-side filtering capabilities.
"""

import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode

import httpx

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria
from scrapers.schemas import NormalizedJob

logger = logging.getLogger(__name__)


class APIAdapter(BaseScraper):
    """Base adapter for REST API job sources with source-side filtering."""
    
    def __init__(
        self,
        base_url: str,
        name: str = "api_adapter",
        enabled: bool = True
    ):
        super().__init__()
        self.base_url = base_url
        self.name = name
        self.enabled = enabled
    
    def get_source_params(self, criteria: SearchCriteria | None = None) -> Dict[str, Any]:
        """Get source-specific query parameters.
        
        Override this method to add source-specific parameter mapping.
        """
        params = super().get_source_params(criteria)
        
        # Add common API parameters
        if criteria:
            if criteria.remote_only:
                params["remote"] = "true"
            if criteria.posted_within_days:
                params["days"] = criteria.posted_within_days
        
        return params
    
    def build_url(self, criteria: SearchCriteria | None = None) -> str:
        """Build URL with query parameters for source-side filtering.
        
        Args:
            criteria: Search criteria
            
        Returns:
            Full URL with query parameters
        """
        params = self.get_source_params(criteria)
        if params:
            query_string = urlencode({k: v for k, v in params.items() if v is not None})
            return f"{self.base_url}?{query_string}"
        return self.base_url
    
    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape jobs from API with source-side filtering.
        
        Args:
            criteria: Search criteria for filtering
            
        Returns:
            List of raw jobs
        """
        jobs: List[RawJob] = []
        
        try:
            url = self.build_url(criteria)
            logger.info(f"{self.name}: Fetching from {url}")
            
            response = self.fetch(url)
            data = response.json()
            
            # Parse response - override in subclass
            jobs = self.parse_response(data)
            
            logger.info(f"{self.name}: Fetched {len(jobs)} jobs")
            
        except Exception as e:
            logger.error(f"{self.name}: Failed to fetch jobs: {e}")
        
        return jobs
    
    def parse_response(self, data: Dict[str, Any] | List) -> List[RawJob]:
        """Parse API response into RawJob objects.
        
        Override this method in subclasses to implement source-specific parsing.
        
        Args:
            data: Parsed JSON response
            
        Returns:
            List of RawJob objects
        """
        # Default implementation - assumes data is a list of job objects
        if isinstance(data, list):
            return [self._parse_job_item(item) for item in data]
        elif isinstance(data, dict) and "jobs" in data:
            return [self._parse_job_item(item) for item in data["jobs"]]
        return []
    
    def _parse_job_item(self, item: Dict[str, Any]) -> RawJob:
        """Parse a single job item from API response.
        
        Override this method in subclasses for source-specific parsing.
        
        Args:
            item: Single job item from API
            
        Returns:
            RawJob object
        """
        return RawJob(
            external_id=self.make_external_id(self.name, str(item.get("id", ""))),
            source=self.name,
            title=item.get("title", ""),
            company=item.get("company", ""),
            url=item.get("url", ""),
            description=item.get("description", ""),
            location=item.get("location", ""),
            salary=item.get("salary", ""),
            posted_at=item.get("posted_at") or item.get("created_at") or item.get("date"),
        )
    
    def to_normalized_job(self, raw_job: RawJob) -> NormalizedJob:
        """Convert RawJob to NormalizedJob.
        
        Override this method to add source-specific normalization.
        
        Args:
            raw_job: RawJob object
            
        Returns:
            NormalizedJob object
        """
        return NormalizedJob.from_raw_job(raw_job)
