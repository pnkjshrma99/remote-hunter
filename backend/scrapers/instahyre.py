"""Instahyre.com scraper - Premium Indian job portal.

Scrapes high-quality jobs from Instahyre with advanced filtering.
"""

import logging
from typing import List, Optional
from urllib.parse import urljoin, quote

from scrapers.base import AuthRequiredError, BaseScraper
from scrapers.filters import RawJob, SearchCriteria
from scrapers.html_parser import HTMLParser

logger = logging.getLogger(__name__)

INSTAHYRE_BASE_URL = "https://www.instahyre.com"
INSTAHYRE_SEARCH_URL = "https://www.instahyre.com/jobs"


class InstahyreScraper(BaseScraper):
    """Instahyre.com job scraper with HTML parsing."""
    
    name = "instahyre"
    
    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape jobs from Instahyre.com."""
        jobs: List[RawJob] = []
        
        try:
            url = self._build_search_url(criteria)
            resp = self.fetch(url)
            html = resp.text
            
            parser = HTMLParser(html, INSTAHYRE_BASE_URL)
            
            # Instahyre job cards
            job_cards = parser.soup.select('.job-card, [class*="JobCard"], .job-item')
            
            if not job_cards:
                # Try alternative selectors
                job_cards = parser.soup.select('div[data-job-id], .job-listing-item')
            
            for card in job_cards:
                try:
                    job = self._parse_job(card, parser)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Failed to parse Instahyre job: {e}")
                    continue
            
            # Deduplicate
            seen = set()
            unique_jobs = []
            for job in jobs:
                if job.external_id not in seen:
                    seen.add(job.external_id)
                    unique_jobs.append(job)
            
            logger.info(f"Instahyre: Found {len(unique_jobs)} jobs")
            return unique_jobs
            
        except AuthRequiredError:
            logger.warning("Instahyre scraper blocked - requires login")
            return []
        except Exception as e:
            logger.error(f"Instahyre scraping failed: {e}")
            return []
    
    def _build_search_url(self, criteria: SearchCriteria | None = None) -> str:
        """Build search URL."""
        keyword = criteria.query if criteria else 'software engineer'
        keyword = quote(keyword)
        
        url = f"{INSTAHYRE_SEARCH_URL}?keywords={keyword}"
        
        if criteria and criteria.remote_only:
            url += "&remote=true"
        
        return url
    
    def _parse_job(self, card, parser: HTMLParser) -> Optional[RawJob]:
        """Parse job from card."""
        try:
            # Extract title
            title_elem = card.select_one('.job-title, h2, h3, [class*="title"]')
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            # Extract company
            company_elem = card.select_one('.company-name, [class*="company"]')
            company = company_elem.get_text(strip=True) if company_elem else ''
            
            # Extract URL
            link_elem = card.select_one('a[href]')
            job_url = link_elem.get('href', '') if link_elem else ''
            if job_url:
                job_url = urljoin(INSTAHYRE_BASE_URL, job_url)
            
            if not title or not company:
                return None
            
            # Extract location
            location_elem = card.select_one('.location, [class*="location"]')
            location = location_elem.get_text(strip=True) if location_elem else 'Remote'
            
            # Extract salary
            salary_elem = card.select_one('.salary, [class*="salary"], [class*="compensation"]')
            salary = salary_elem.get_text(strip=True) if salary_elem else ''
            
            # Extract experience
            exp_elem = card.select_one('.experience, [class*="experience"]')
            experience = exp_elem.get_text(strip=True) if exp_elem else ''
            
            # Extract skills
            skills_elem = card.select_one('.skills, [class*="skill"]')
            skills = skills_elem.get_text(strip=True) if skills_elem else ''
            
            # Extract posted date
            posted_elem = card.select_one('.posted-date, [class*="posted"], [class*="date"]')
            posted_at = posted_elem.get_text(strip=True) if posted_elem else ''
            
            # Generate external ID
            external_id = self.make_external_id(self.name, job_url, title)
            
            # Build description
            description_parts = []
            if experience:
                description_parts.append(f"Experience: {experience}")
            if skills:
                description_parts.append(f"Skills: {skills}")
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
            parser = HTMLParser(html, INSTAHYRE_BASE_URL)
            
            details = parser.extract_job_details()
            return details
            
        except Exception as e:
            logger.warning(f"Failed to fetch job details for {job_url}: {e}")
            return None
