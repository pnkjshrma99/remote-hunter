"""Playwright adapter for JavaScript-rendered pages.

This adapter uses Playwright to scrape pages that require JavaScript
rendering, such as Single Page Applications (SPAs).
"""

import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria
from scrapers.schemas import NormalizedJob

logger = logging.getLogger(__name__)


class PlaywrightAdapter(BaseScraper):
    """Base adapter for JavaScript-rendered pages using Playwright."""
    
    def __init__(
        self,
        base_url: str,
        name: str = "playwright_adapter",
        enabled: bool = False,  # Disabled by default as it requires Playwright
    ):
        super().__init__()
        self.base_url = base_url
        self.name = name
        self.enabled = enabled
        self._playwright_available = self._check_playwright()
    
    def _check_playwright(self) -> bool:
        """Check if Playwright is available."""
        try:
            from playwright.sync_api import sync_playwright
            return True
        except ImportError:
            logger.warning(f"{self.name}: Playwright not installed, adapter disabled")
            return False
    
    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape jobs from JavaScript-rendered page.
        
        Args:
            criteria: Search criteria for filtering
            
        Returns:
            List of raw jobs
        """
        if not self._playwright_available:
            logger.error(f"{self.name}: Playwright not available")
            return []
        
        jobs: List[RawJob] = []
        
        try:
            from playwright.sync_api import sync_playwright
            
            url = self.build_url(criteria)
            logger.info(f"{self.name}: Scraping {url} with Playwright")
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Navigate to page
                page.goto(url, wait_until="networkidle")
                
                # Wait for job listings to load
                self.wait_for_jobs(page)
                
                # Extract job data
                jobs = self.extract_jobs(page)
                
                browser.close()
            
            logger.info(f"{self.name}: Fetched {len(jobs)} jobs")
            
        except Exception as e:
            logger.error(f"{self.name}: Failed to scrape with Playwright: {e}")
        
        return jobs
    
    def build_url(self, criteria: SearchCriteria | None = None) -> str:
        """Build URL with query parameters.
        
        Override this method in subclasses to add source-specific URL building.
        
        Args:
            criteria: Search criteria
            
        Returns:
            Full URL
        """
        params = self.get_source_params(criteria)
        if params:
            from urllib.parse import urlencode
            query_string = urlencode({k: v for k, v in params.items() if v is not None})
            return f"{self.base_url}?{query_string}"
        return self.base_url
    
    def wait_for_jobs(self, page) -> None:
        """Wait for job listings to load on the page.
        
        Override this method in subclasses to implement source-specific waiting logic.
        
        Args:
            page: Playwright page object
        """
        # Default: wait for a common job listing selector
        try:
            page.wait_for_selector(".job-card, .job-listing, [data-job]", timeout=10000)
        except:
            # If selector not found, just wait a bit
            page.wait_for_timeout(2000)
    
    def extract_jobs(self, page) -> List[RawJob]:
        """Extract job data from the page.
        
        Override this method in subclasses to implement source-specific extraction.
        
        Args:
            page: Playwright page object
            
        Returns:
            List of RawJob objects
        """
        jobs = []
        
        # Try to find job cards using common selectors
        selectors = [
            ".job-card",
            ".job-listing",
            "[data-job]",
            ".job-item",
            ".posting",
        ]
        
        job_elements = []
        for selector in selectors:
            elements = page.query_selector_all(selector)
            if elements:
                job_elements = elements
                break
        
        for element in job_elements:
            try:
                job = self._extract_job_element(element)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.warning(f"{self.name}: Failed to extract job element: {e}")
        
        return jobs
    
    def _extract_job_element(self, element) -> Optional[RawJob]:
        """Extract job data from a single job element.
        
        Override this method in subclasses for source-specific extraction.
        
        Args:
            element: Playwright element object
            
        Returns:
            RawJob object or None
        """
        # Default extraction - try common selectors
        title_el = element.query_selector(".title, h2, h3, .job-title")
        company_el = element.query_selector(".company, .company-name, h4")
        url_el = element.query_selector("a[href]")
        location_el = element.query_selector(".location, .job-location")
        desc_el = element.query_selector(".description, .job-description")
        
        title = title_el.text_content().strip() if title_el else ""
        company = company_el.text_content().strip() if company_el else ""
        url = url_el.get_attribute("href") if url_el else ""
        location = location_el.text_content().strip() if location_el else ""
        description = desc_el.text_content().strip() if desc_el else ""
        
        # Make URL absolute if relative
        if url and not url.startswith("http"):
            url = urljoin(self.base_url, url)
        
        if not title or not url:
            return None
        
        return RawJob(
            external_id=self.make_external_id(self.name, url, title),
            source=self.name,
            title=title,
            company=company or "Unknown",
            url=url,
            description=description,
            location=location,
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
