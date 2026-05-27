"""AngelList/Wellfound jobs scraper.

Wellfound (formerly AngelList) has a public jobs page at
https://wellfound.com/jobs that can be scraped without auth.
Individual job listings are also accessible via their public URLs.

The GraphQL API at api.wellfound.com requires authentication,
so we scrape the public HTML website instead.
"""

import logging
import re
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

WELLFOUND_URL = "https://wellfound.com/jobs"


class AngelListScraper(BaseScraper):
    name = "angellist"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape Wellfound (public website) for remote jobs."""
        jobs: List[RawJob] = []
        
        search_query = "remote"
        if criteria and criteria.query:
            search_query = f"remote+{criteria.query.replace(' ', '+')}"
        
        url = f"{WELLFOUND_URL}?q={search_query}"
        
        # Strategy 1: Try Playwright (handles JS-rendered content)
        playwright_jobs = self._scrape_with_playwright(url)
        if playwright_jobs:
            logger.info(f"Playwright returned {len(playwright_jobs)} jobs from Wellfound")
            return playwright_jobs
        
        # Strategy 2: Fallback to the JSON API with a simple GET
        # Wellfound has a public API endpoint used by their own pages
        api_jobs = self._scrape_with_public_api(criteria)
        if api_jobs:
            logger.info(f"API returned {len(api_jobs)} jobs from Wellfound")
            return api_jobs
        
        logger.warning("All scraping strategies failed for Wellfound")
        return jobs

    def _scrape_with_playwright(self, url: str) -> List[RawJob]:
        """Use Playwright to scrape JS-rendered Wellfound jobs page."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return []
        
        jobs: List[RawJob] = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                )
                page = context.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                
                # Wait for job listings to load
                page.wait_for_selector('[data-testid="job-card"], .job-card, [class*="job"]', timeout=15000)
                
                # Get job cards
                job_cards = page.query_selector_all('[data-testid="job-card"]')
                if not job_cards:
                    job_cards = page.query_selector_all('[class*="job"] a[href*="/jobs/"]')
                
                for card in job_cards:
                    try:
                        href = card.get_attribute("href")
                        if not href or "/jobs/" not in href:
                            continue
                        if not href.startswith("http"):
                            href = f"https://wellfound.com{href}"
                        
                        # Extract title
                        title_el = card.query_selector("h2, h3, [class*='title']")
                        title = title_el.text_content().strip() if title_el else ""
                        
                        # Extract company
                        company_el = card.query_selector("[class*='company'], [class*='org']")
                        company = company_el.text_content().strip() if company_el else "Unknown"
                        
                        if not title:
                            continue
                        
                        external_id = self.make_external_id(self.name, href, title)
                        jobs.append(
                            RawJob(
                                external_id=external_id,
                                source=self.name,
                                title=title,
                                company=company,
                                url=href,
                                location="Remote",
                            )
                        )
                    except Exception:
                        continue
                
                browser.close()
            
        except Exception as e:
            logger.warning(f"Wellfound Playwright scrape failed: {e}")
        
        return jobs

    def _scrape_with_public_api(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Use Wellfound's public API endpoint (used internally by their pages)."""
        jobs: List[RawJob] = []
        try:
            # Wellfound has a public search/listing endpoint
            search_query = "remote"
            if criteria and criteria.query:
                search_query = f"remote {criteria.query}"
            
            api_url = f"{WELLFOUND_URL}.json"
            if criteria and criteria.query:
                api_url += f"?query={criteria.query.replace(' ', '+')}"
            
            resp = self.fetch(api_url)
            data = resp.json()
            
            # Handle various response formats
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("jobs", data.get("data", data.get("results", [])))
            else:
                items = []
            
            for item in items:
                if isinstance(item, dict):
                    title = item.get("title", "") or item.get("name", "")
                    company = item.get("company_name", "") or item.get("company", {}).get("name", "Unknown")
                    url = item.get("url", "") or item.get("absolute_url", "")
                    if url and not url.startswith("http"):
                        url = f"https://wellfound.com{url}"
                    description = (item.get("description", "") or item.get("high_concept", "") or "")
                    
                    if not title:
                        continue
                    
                    external_id = self.make_external_id(self.name, url, title)
                    jobs.append(
                        RawJob(
                            external_id=external_id,
                            source=self.name,
                            title=title,
                            company=company,
                            url=url,
                            description=description if isinstance(description, str) else str(description),
                            location=item.get("location", "Remote"),
                            salary=item.get("salary", ""),
                        )
                    )
            
        except Exception as e:
            logger.debug(f"Wellfound public API failed: {e}")
        
        return jobs