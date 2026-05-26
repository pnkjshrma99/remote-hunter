"""Wellfound (AngelList) Jobs Scraper

Fetches jobs from Wellfound (formerly AngelList) using their GraphQL API.
"""

import logging
from typing import List, Optional
from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)


class WellfoundScraper(BaseScraper):
    """Wellfound (AngelList) job scraper"""

    name = "wellfound"
    BASE_URL = "https://www.wellfound.com"
    API_URL = "https://api.wellfound.com/graphql"
    
    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """
        Scrape jobs from Wellfound.
        
        Note: Wellfound requires authentication for their GraphQL API.
        This is a placeholder implementation that would need API credentials.
        """
        jobs: List[RawJob] = []
        
        try:
            # GraphQL query for remote jobs
            query = """
            query Jobs($filter: JobFilterInput) {
                jobs(filter: $filter) {
                    id
                    title
                    companyName
                    slug
                    description
                    locationType
                    salaryRange {
                        minCompensation
                        maxCompensation
                        currency
                    }
                    createdAt
                }
            }
            """
            
            search_query = "remote"
            if criteria and hasattr(criteria, 'query') and criteria.query:
                search_query = criteria.query
            
            variables = {
                "filter": {
                    "query": search_query,
                    "locationType": "REMOTE",
                    "limit": 50
                }
            }
            
            # This would require authentication
            # For now, return empty list
            logger.warning("Wellfound scraper requires API authentication. Skipping.")
            
        except Exception as e:
            logger.error(f"Error fetching Wellfound jobs: {e}")
        
        return jobs
    
    def _parse_job(self, job_data: dict) -> RawJob:
        """Parse job data from API response"""
        salary_info = job_data.get('salaryRange', {})
        salary = ""
        if salary_info:
            min_sal = salary_info.get('minCompensation')
            max_sal = salary_info.get('maxCompensation')
            currency = salary_info.get('currency', 'USD')
            if min_sal and max_sal:
                salary = f"{currency} {min_sal:,} - {max_sal:,}"
        
        external_id = self.make_external_id(
            self.name,
            str(job_data.get('id', '')),
            job_data.get('title', '')
        )
        return RawJob(
            external_id=external_id,
            source=self.name,
            title=job_data.get('title', ''),
            company=job_data.get('companyName', ''),
            url=f"{self.BASE_URL}/jobs/{job_data.get('slug', '')}",
            description=job_data.get('description', ''),
            location="Remote" if job_data.get('locationType') == 'REMOTE' else job_data.get('locationType', ''),
            salary=salary,
            posted_at=job_data.get('createdAt', '')
        )