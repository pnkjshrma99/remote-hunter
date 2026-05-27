"""GraphQL adapter for GraphQL-based job boards.

This adapter provides a base for GraphQL scrapers with query building
and response parsing capabilities.
"""

import logging
from typing import List, Dict, Any, Optional

import httpx

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria
from scrapers.schemas import NormalizedJob

logger = logging.getLogger(__name__)


class GraphQLAdapter(BaseScraper):
    """Base adapter for GraphQL-based job sources."""
    
    def __init__(
        self,
        endpoint_url: str,
        name: str = "graphql_adapter",
        enabled: bool = True
    ):
        super().__init__()
        self.endpoint_url = endpoint_url
        self.name = name
        self.enabled = enabled
    
    def build_query(self, criteria: SearchCriteria | None = None) -> str:
        """Build GraphQL query with filters.
        
        Override this method in subclasses to implement source-specific queries.
        
        Args:
            criteria: Search criteria
            
        Returns:
            GraphQL query string
        """
        # Default query - override in subclass
        return """
        query {
            jobs {
                id
                title
                company
                url
                description
                location
                salary
                postedAt
            }
        }
        """
    
    def build_variables(self, criteria: SearchCriteria | None = None) -> Dict[str, Any]:
        """Build GraphQL variables from search criteria.
        
        Override this method in subclasses to add source-specific variable mapping.
        
        Args:
            criteria: Search criteria
            
        Returns:
            Dictionary of GraphQL variables
        """
        variables = {}
        
        if criteria:
            if criteria.query:
                variables["query"] = criteria.query
            if criteria.remote_only:
                variables["remote"] = True
            if criteria.location:
                variables["location"] = criteria.location
            if criteria.posted_within_days:
                variables["postedWithinDays"] = criteria.posted_within_days
            if criteria.min_experience is not None:
                variables["experienceMin"] = criteria.min_experience
            if criteria.max_experience is not None:
                variables["experienceMax"] = criteria.max_experience
        
        return variables
    
    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape jobs from GraphQL endpoint.
        
        Args:
            criteria: Search criteria for filtering
            
        Returns:
            List of raw jobs
        """
        jobs: List[RawJob] = []
        
        try:
            query = self.build_query(criteria)
            variables = self.build_variables(criteria)
            
            logger.info(f"{self.name}: Executing GraphQL query with variables: {variables}")
            
            response = self._execute_query(query, variables)
            data = response.json()
            
            # Parse response
            jobs = self.parse_response(data)
            
            logger.info(f"{self.name}: Fetched {len(jobs)} jobs")
            
        except Exception as e:
            logger.error(f"{self.name}: Failed to fetch jobs: {e}")
        
        return jobs
    
    def _execute_query(self, query: str, variables: Dict[str, Any]) -> httpx.Response:
        """Execute GraphQL query.
        
        Args:
            query: GraphQL query string
            variables: GraphQL variables
            
        Returns:
            HTTP response
        """
        payload = {
            "query": query,
            "variables": variables
        }
        
        headers = self._headers()
        headers["Content-Type"] = "application/json"
        
        response = self.fetch(self.endpoint_url, json=payload, headers=headers)
        return response
    
    def parse_response(self, data: Dict[str, Any]) -> List[RawJob]:
        """Parse GraphQL response into RawJob objects.
        
        Override this method in subclasses to implement source-specific parsing.
        
        Args:
            data: Parsed JSON response
            
        Returns:
            List of RawJob objects
        """
        # Check for errors
        if "errors" in data:
            logger.error(f"{self.name}: GraphQL errors: {data['errors']}")
            return []
        
        # Extract data - override in subclass
        if "data" in data:
            data = data["data"]
        
        # Default implementation - assumes data has a "jobs" field
        if "jobs" in data:
            return [self._parse_job_item(item) for item in data["jobs"]]
        
        return []
    
    def _parse_job_item(self, item: Dict[str, Any]) -> RawJob:
        """Parse a single job item from GraphQL response.
        
        Override this method in subclasses for source-specific parsing.
        
        Args:
            item: Single job item from GraphQL
            
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
            posted_at=item.get("postedAt") or item.get("posted_at") or item.get("created_at"),
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
