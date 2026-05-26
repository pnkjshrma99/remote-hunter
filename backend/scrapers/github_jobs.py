"""GitHub Jobs Scraper

Fetches jobs from GitHub Jobs API.
"""

import logging
from typing import List, Optional
from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)


class GitHubJobsScraper(BaseScraper):
    """GitHub Jobs API scraper"""

    name = "github_jobs"
    BASE_URL = "https://jobs.github.com/positions.json"
    
    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """
        Scrape jobs from GitHub Jobs API.
        
        Note: GitHub Jobs API was deprecated in 2021.
        This is a placeholder implementation.
        """
        jobs: List[RawJob] = []
        
        try:
            params = {
                'full_time': 'true',
                'location': 'remote'
            }
            
            if criteria and hasattr(criteria, 'query') and criteria.query:
                params['description'] = criteria.query
            
            resp = self.fetch(self.BASE_URL, params=params)
            data = resp.json()
            
            if isinstance(data, list):
                for item in data:
                    job = self._parse_job(item)
                    if job:
                        jobs.append(job)
            
            logger.info(f"Fetched {len(jobs)} jobs from GitHub Jobs")
            
        except Exception as e:
            logger.error(f"Error fetching GitHub Jobs: {e}")
        
        return jobs
    
    def _parse_job(self, job_data: dict) -> Optional[RawJob]:
        """Parse job data from API response"""
        try:
            external_id = self.make_external_id(
                self.name,
                job_data.get('url', ''),
                job_data.get('title', '')
            )
            return RawJob(
                external_id=external_id,
                source=self.name,
                title=job_data.get('title', ''),
                company=job_data.get('company', ''),
                url=job_data.get('url', ''),
                description=job_data.get('description', ''),
                location=job_data.get('location', 'Remote'),
                salary='',
                posted_at=job_data.get('created_at', '')
            )
        except Exception as e:
            logger.error(f"Error parsing job: {e}")
            return None