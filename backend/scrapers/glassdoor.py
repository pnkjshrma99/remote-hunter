"""Glassdoor.com scraper - Global job portal with company reviews.

Scrapes jobs from Glassdoor with company information and reviews.
"""

import logging
from typing import List, Optional
from urllib.parse import urljoin, quote

from scrapers.base import AuthRequiredError, BaseScraper
from scrapers.filters import RawJob, SearchCriteria
from scrapers.html_parser import HTMLParser

logger = logging.getLogger(__name__)

GLASSDOOR_BASE_URL = "https://www.glassdoor.com"
GLASSDOOR_SEARCH_URL = "https://www.glassdoor.com/Job/jobs.htm"


class GlassdoorScraper(BaseScraper):
    """Glassdoor.com job scraper with HTML parsing."""
    
    name = "glassdoor"
    
    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape jobs from Glassdoor.com."""
        jobs: List[RawJob] = []
        
        try:
            url = self._build_search_url(criteria)
            resp = self.fetch(url)
            html = resp.text
            
            parser = HTMLParser(html, GLASSDOOR_BASE_URL)
            
            # Glassdoor job listings
            job_cards = parser.soup.select('.jobCard, [class*="JobCard"], .jl')
            
            if not job_cards:
                # Try alternative selectors
                job_cards = parser.soup.select('li[data-testid="jobListing"], .job-listing')
            
            for card in job_cards:
                try:
                    job = self._parse_job(card, parser)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Failed to parse Glassdoor job: {e}")
                    continue
            
            # Deduplicate
            seen = set()
            unique_jobs = []
            for job in jobs:
                if job.external_id not in seen:
                    seen.add(job.external_id)
                    unique_jobs.append(job)
            
            logger.info(f"Glassdoor: Found {len(unique_jobs)} jobs")
            return unique_jobs
            
        except AuthRequiredError:
            logger.warning("Glassdoor scraper blocked - requires login/cookies/headers")
            return []
        except Exception as e:
            logger.error(f"Glassdoor scraping failed: {e}")
            return []
    
    def _build_search_url(self, criteria: SearchCriteria | None = None) -> str:
        """Build search URL."""
        keyword = criteria.query if criteria else 'software engineer'
        keyword = quote(keyword)
        
        url = f"{GLASSDOOR_SEARCH_URL}?sc.keyword={keyword}"
        
        if criteria and criteria.remote_only:
            url += "&sc.locationType=REMOTE_ONLY"
        
        return url
    
    def _parse_job(self, card, parser: HTMLParser) -> Optional[RawJob]:
        """Parse job from card."""
        try:
            # Extract title
            title_elem = card.select_one('.jobTitle, a[data-testid="job-title"], h2')
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            # Extract company
            company_elem = card.select_one('.css-1x7z1ps, [data-testid="company-name"], .companyName')
            company = company_elem.get_text(strip=True) if company_elem else ''
            
            # Extract URL
            link_elem = card.select_one('a[href]')
            job_url = link_elem.get('href', '') if link_elem else ''
            if job_url:
                job_url = urljoin(GLASSDOOR_BASE_URL, job_url)
            
            if not title or not company:
                return None
            
            # Extract location
            location_elem = card.select_one('.location, [data-testid="job-location"]')
            location = location_elem.get_text(strip=True) if location_elem else 'Remote'
            
            # Extract salary
            salary_elem = card.select_one('.salary, [data-testid="salary"]')
            salary = salary_elem.get_text(strip=True) if salary_elem else ''
            
            # Extract rating
            rating_elem = card.select_one('.rating, [data-testid="rating"]')
            rating = rating_elem.get_text(strip=True) if rating_elem else ''
            
            # Extract posted date
            posted_elem = card.select_one('.posted-date, [data-testid="posted-date"]')
            posted_at = posted_elem.get_text(strip=True) if posted_elem else ''
            
            # Generate external ID
            external_id = self.make_external_id(self.name, job_url, title)
            
            # Build description with company rating
            description_parts = []
            if rating:
                description_parts.append(f"Company Rating: {rating}")
            description = " | ".join(description_parts)
            
            return RawJob(
                external_id=external_id,
                source=self.name,
                title=title,
                company=company,
                url=job_url,
                description=description,
                location=location,
                salary=salary,
                posted_at=posted_at
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse job: {e}")
            return None
    
    def _fetch_job_details(self, job_url: str) -> Optional[dict]:
        """Fetch detailed job information from job page."""
        try:
            resp = self.fetch(job_url)
            html = resp.text
            parser = HTMLParser(html, GLASSDOOR_BASE_URL)
            
            details = parser.extract_job_details()
            return details
            
        except Exception as e:
            logger.warning(f"Failed to fetch job details for {job_url}: {e}")
            return None
