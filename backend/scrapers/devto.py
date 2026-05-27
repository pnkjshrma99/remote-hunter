"""Dev.to Jobs Scraper

Fetches jobs from Dev.to API - the largest developer community platform.
Dev.to has a robust API that returns classified listings including jobs.
"""

import logging
from typing import List, Optional
from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)


class DevToScraper(BaseScraper):
    """Dev.to API scraper for job listings"""

    name = "devto"
    BASE_URL = "https://dev.to/api"
    
    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """
        Scrape jobs from Dev.to API.
        
        FIXED: Correct API parameters - uses proper Dev.to API endpoints:
        - /api/listings with category=cfp (call for proposals = jobs)
        - /api/articles with tags=job+hiring
        """
        jobs: List[RawJob] = []
        
        try:
            import httpx
            
            # FIX: Use correct Dev.to API endpoint for job listings
            # Dev.to classified listings are fetched via /api/listings
            # Category "cfp" = "Call for Proposals" which includes job posts
            listing_urls = [
                f"{self.BASE_URL}/listings?category=jobs",
                f"{self.BASE_URL}/articles?tag=jobs&per_page=50",
                f"{self.BASE_URL}/articles?tag=hiring&per_page=50",
            ]
            
            seen_urls = set()
            
            for url in listing_urls:
                try:
                    resp = self.fetch(url)
                    data = resp.json()
                    
                    if isinstance(data, list):
                        for item in data:
                            title = item.get("title", "")
                            url_value = item.get("url", "") or item.get("slug", "")
                            
                            # Skip if we've already seen this URL
                            if url_value in seen_urls:
                                continue
                            seen_urls.add(url_value)
                            
                            # Dev.to listings may have user/org info nested
                            user = item.get("user", {}) or {}
                            org = item.get("organization", {}) or {}
                            company = org.get("name", "") or user.get("username", "") or "Dev.to Community"
                            
                            description = item.get("body_markdown", "") or item.get("body_text", "") or item.get("description", "") or ""
                            
                            location = item.get("location", "") or "Remote"
                            
                            # Tags may indicate remote
                            tags = item.get("tags", []) or item.get("tag_list", [])
                            if isinstance(tags, list) and any("remote" in t.lower() for t in tags):
                                location = "Remote"
                            
                            # Convert tags to a descriptive string
                            if isinstance(tags, list) and not description:
                                description = f"Tags: {', '.join(tags)}"
                            
                            external_id = self.make_external_id(
                                self.name,
                                str(item.get("id", url_value)),
                                title
                            )
                            jobs.append(RawJob(
                                external_id=external_id,
                                source=self.name,
                                title=title,
                                company=company,
                                url=url_value,
                                description=description,
                                location=location,
                                posted_at=str(item.get("created_at", item.get("published_at", ""))),
                            ))
                except Exception as e:
                    logger.debug("Dev.to URL %s failed: %s", url, e)
                    continue
            
            logger.info(f"Fetched {len(jobs)} jobs from Dev.to")
            
        except Exception as e:
            logger.error(f"Error fetching Dev.to jobs: {e}")
        
        return jobs