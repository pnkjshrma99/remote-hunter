"""Unstop.com scraper - Student and fresher job portal.

Scrapes internships, fresher jobs, and opportunities from Unstop.
"""

import logging
from typing import List, Optional
from urllib.parse import urljoin, quote

from scrapers.base import AuthRequiredError, BaseScraper
from scrapers.filters import RawJob, SearchCriteria
from scrapers.html_parser import HTMLParser

logger = logging.getLogger(__name__)

UNSTOP_BASE_URL = "https://unstop.com"
UNSTOP_SEARCH_URL = "https://unstop.com/opportunities"


class UnstopScraper(BaseScraper):
    """Unstop.com job scraper for students and freshers."""
    
    name = "unstop"
    
    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape jobs from Unstop.com."""
        jobs: List[RawJob] = []
        
        try:
            url = self._build_search_url(criteria)
            resp = self.fetch(url)
            html = resp.text
            
            parser = HTMLParser(html, UNSTOP_BASE_URL)
            
            # Unstop opportunity cards
            job_cards = parser.soup.select('.opportunity-card, [class*="OpportunityCard"], .card')
            
            if not job_cards:
                # Try alternative selectors
                job_cards = parser.soup.select('.opportunity-item, .job-card, .challenge-card')
            
            for card in job_cards:
                try:
                    job = self._parse_job(card, parser)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Failed to parse Unstop job: {e}")
                    continue
            
            # Deduplicate
            seen = set()
            unique_jobs = []
            for job in jobs:
                if job.external_id not in seen:
                    seen.add(job.external_id)
                    unique_jobs.append(job)
            
            logger.info(f"Unstop: Found {len(unique_jobs)} jobs")
            return unique_jobs
            
        except AuthRequiredError:
            logger.warning("Unstop scraper blocked - requires login")
            return []
        except Exception as e:
            logger.error(f"Unstop scraping failed: {e}")
            return []
    
    def _build_search_url(self, criteria: SearchCriteria | None = None) -> str:
        """Build search URL."""
        keyword = criteria.query if criteria else 'software'
        keyword = quote(keyword)
        
        url = f"{UNSTOP_SEARCH_URL}?search={keyword}"
        
        return url
    
    def _parse_job(self, card, parser: HTMLParser) -> Optional[RawJob]:
        """Parse job from card."""
        try:
            # Extract title
            title_elem = card.select_one('.opportunity-title, h3, h4, [class*="title"]')
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            # Extract company
            company_elem = card.select_one('.company-name, [class*="company"], .organization')
            company = company_elem.get_text(strip=True) if company_elem else ''
            
            # Extract URL
            link_elem = card.select_one('a[href]')
            job_url = link_elem.get('href', '') if link_elem else ''
            if job_url:
                job_url = urljoin(UNSTOP_BASE_URL, job_url)
            
            if not title:
                return None
            
            # If no company, use "Unstop" or extract from URL
            if not company:
                company = "Unstop Opportunity"
            
            # Extract location
            location_elem = card.select_one('.location, [class*="location"]')
            location = location_elem.get_text(strip=True) if location_elem else 'Remote'
            
            # Extract type (internship/job)
            type_elem = card.select_one('.type, [class*="type"], .badge')
            job_type = type_elem.get_text(strip=True) if type_elem else ''
            
            # Extract deadline
            deadline_elem = card.select_one('.deadline, [class*="deadline"], .date')
            posted_at = deadline_elem.get_text(strip=True) if deadline_elem else ''
            
            # Generate external ID
            external_id = self.make_external_id(self.name, job_url, title)
            
            # Build description
            description_parts = []
            if job_type:
                description_parts.append(f"Type: {job_type}")
            description = " | ".join(description_parts)
            
            return RawJob(
                external_id=external_id,
                source=self.name,
                title=title,
                company=company,
                url=job_url,
                description=description,
                location=location,
                salary='',
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
            parser = HTMLParser(html, UNSTOP_BASE_URL)
            
            details = parser.extract_job_details()
            return details
            
        except Exception as e:
            logger.warning(f"Failed to fetch job details for {job_url}: {e}")
            return None
