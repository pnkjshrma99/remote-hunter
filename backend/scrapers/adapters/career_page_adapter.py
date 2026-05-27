"""Company career page adapter.

This adapter provides a base for scraping company career pages directly,
which often have higher quality and more up-to-date job postings.
"""

import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria
from scrapers.schemas import NormalizedJob

logger = logging.getLogger(__name__)


class CareerPageAdapter(BaseScraper):
    """Base adapter for company career pages."""
    
    def __init__(
        self,
        company_name: str,
        career_url: str,
        name: Optional[str] = None,
        enabled: bool = True
    ):
        super().__init__()
        self.company_name = company_name
        self.career_url = career_url
        self.name = name or f"career_{company_name.lower().replace(' ', '_')}"
        self.enabled = enabled
    
    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape jobs from company career page.
        
        Args:
            criteria: Search criteria for filtering
            
        Returns:
            List of raw jobs
        """
        jobs: List[RawJob] = []
        
        try:
            logger.info(f"{self.name}: Scraping career page for {self.company_name}")
            
            # Fetch career page
            response = self.fetch(self.career_url)
            
            # Extract job data
            jobs = self.extract_jobs(response.text)
            
            # Apply post-fetch filtering based on criteria
            if criteria:
                jobs = self.filter_jobs(jobs, criteria)
            
            logger.info(f"{self.name}: Fetched {len(jobs)} jobs")
            
        except Exception as e:
            logger.error(f"{self.name}: Failed to scrape career page: {e}")
        
        return jobs
    
    def extract_jobs(self, html: str) -> List[RawJob]:
        """Extract job data from career page HTML.
        
        Override this method in subclasses to implement company-specific extraction.
        
        Args:
            html: Career page HTML
            
        Returns:
            List of RawJob objects
        """
        from bs4 import BeautifulSoup
        
        jobs = []
        soup = BeautifulSoup(html, "html.parser")
        
        # Try common career page selectors
        selectors = [
            "a[href*='/jobs/']",
            "a[href*='/careers/']",
            ".job-posting",
            ".job-listing",
            "[data-job]",
            ".posting",
        ]
        
        job_links = []
        for selector in selectors:
            links = soup.select(selector)
            if links:
                job_links = links
                break
        
        for link in job_links:
            try:
                job = self._extract_job_link(link)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.warning(f"{self.name}: Failed to extract job link: {e}")
        
        return jobs
    
    def _extract_job_link(self, link) -> Optional[RawJob]:
        """Extract job data from a job link element.
        
        Override this method in subclasses for company-specific extraction.
        
        Args:
            link: BeautifulSoup link element
            
        Returns:
            RawJob object or None
        """
        href = link.get("href", "")
        text = link.get_text(strip=True)
        
        if not href or not text:
            return None
        
        # Make URL absolute
        if not href.startswith("http"):
            href = urljoin(self.career_url, href)
        
        return RawJob(
            external_id=self.make_external_id(self.name, href, text),
            source=self.name,
            title=text,
            company=self.company_name,
            url=href,
            location="",  # Will be filled when fetching individual job page
        )
    
    def filter_jobs(self, jobs: List[RawJob], criteria: SearchCriteria) -> List[RawJob]:
        """Filter jobs based on search criteria.
        
        Args:
            jobs: List of jobs to filter
            criteria: Search criteria
            
        Returns:
            Filtered list of jobs
        """
        filtered = []
        
        for job in jobs:
            # Check title match
            if criteria.query and criteria.query.lower() not in job.title.lower():
                continue
            
            # Check remote if required
            if criteria.remote_only and "remote" not in job.title.lower():
                continue
            
            filtered.append(job)
        
        return filtered
    
    def fetch_job_details(self, job_url: str) -> Dict[str, Any]:
        """Fetch detailed job information from individual job page.
        
        Override this method in subclasses for company-specific detail extraction.
        
        Args:
            job_url: URL of individual job page
            
        Returns:
            Dictionary of job details
        """
        try:
            response = self.fetch(job_url)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            
            details = {
                "description": self._extract_description(soup),
                "location": self._extract_location(soup),
                "salary": self._extract_salary(soup),
            }
            
            return details
            
        except Exception as e:
            logger.error(f"{self.name}: Failed to fetch job details: {e}")
            return {}
    
    def _extract_description(self, soup) -> str:
        """Extract job description from job page.
        
        Override this method in subclasses for company-specific extraction.
        """
        selectors = [
            ".job-description",
            ".description",
            "[data-description]",
            "#job-description",
        ]
        
        for selector in selectors:
            el = soup.select_one(selector)
            if el:
                return el.get_text(strip=True)
        
        return ""
    
    def _extract_location(self, soup) -> str:
        """Extract job location from job page.
        
        Override this method in subclasses for company-specific extraction.
        """
        selectors = [
            ".location",
            ".job-location",
            "[data-location]",
        ]
        
        for selector in selectors:
            el = soup.select_one(selector)
            if el:
                return el.get_text(strip=True)
        
        return ""
    
    def _extract_salary(self, soup) -> str:
        """Extract job salary from job page.
        
        Override this method in subclasses for company-specific extraction.
        """
        selectors = [
            ".salary",
            ".compensation",
            "[data-salary]",
        ]
        
        for selector in selectors:
            el = soup.select_one(selector)
            if el:
                return el.get_text(strip=True)
        
        return ""
    
    def to_normalized_job(self, raw_job: RawJob) -> NormalizedJob:
        """Convert RawJob to NormalizedJob.
        
        Override this method to add source-specific normalization.
        
        Args:
            raw_job: RawJob object
            
        Returns:
            NormalizedJob object
        """
        return NormalizedJob.from_raw_job(raw_job)
