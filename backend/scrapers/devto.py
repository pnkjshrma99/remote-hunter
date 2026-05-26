"""Dev.to Jobs Scraper

Fetches jobs from Dev.to Jobs API.
"""

import logging
from typing import List, Optional
from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)


class DevToScraper(BaseScraper):
    """Dev.to Jobs API scraper"""

    name = "devto"
    BASE_URL = "https://dev.to/api/listings"
    
    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """
        Scrape jobs from Dev.to Jobs API.
        """
        jobs: List[RawJob] = []
        
        try:
            params = {
                'category': 'jobs',
                'tag': 'remote'
            }
            
            if criteria and hasattr(criteria, 'query') and criteria.query:
                params['search'] = criteria.query
            
            resp = self.fetch(self.BASE_URL, params=params)
            data = resp.json()
            
            if isinstance(data, list):
                for item in data:
                    job = self._parse_job(item)
                    if job:
                        jobs.append(job)
            
            logger.info(f"Fetched {len(jobs)} jobs from Dev.to")
            
        except Exception as e:
            logger.error(f"Error fetching Dev.to jobs: {e}")
        
        return jobs
    
    def _parse_job(self, job_data: dict) -> Optional[RawJob]:
        """Parse job data from API response"""
        try:
            external_id = self.make_external_id(
                self.name,
                str(job_data.get('id', '')),
                job_data.get('title', '')
            )
            return RawJob(
                external_id=external_id,
                source=self.name,
                title=job_data.get('title', ''),
                company=job_data.get('company_name', ''),
                url=job_data.get('url', ''),
                description=job_data.get('description', ''),
                location=job_data.get('location', 'Remote'),
                salary=job_data.get('tag_list', ''),
                posted_at=job_data.get('created_at', '')
            )
        except Exception as e:
            logger.error(f"Error parsing job: {e}")
            return None