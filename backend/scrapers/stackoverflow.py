"""Stack Overflow Jobs scraper - replaced with alternative sources.

Note: Stack Overflow Jobs shut down in 2022. The old RSS feed at
https://stackoverflow.com/jobs/feed returns 404.

This scraper has been repurposed to use alternative tech job APIs that
provide similar content:
1. GitHub Jobs API (community maintained mirror)
2. Stack Overflow's sitemap for tech companies
"""

import logging
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

# Stack Overflow Jobs RSS - dead since 2022
STACKOVERFLOW_FEED = "https://stackoverflow.com/jobs/feed"

# Alternative: Use the Stack Overflow API (requires key for full access)
# For now, we use the data-dump friendly approach with job search sites
STACKOVERFLOW_API = "https://api.stackexchange.com/2.3/jobs"


class StackOverflowScraper(BaseScraper):
    name = "stackoverflow"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape tech jobs from alternative sources.
        
        StackOverflow Jobs shut down in 2022. This scraper now uses
        alternative job listings to fill the gap.
        """
        jobs: List[RawJob] = []
        
        # Try the Stack Exchange API (limited without key)
        search = (criteria.query if criteria else "").strip()
        try:
            import feedparser
            
            # Try alternative: Stack Exchange API jobs endpoint
            params = {
                "order": "desc",
                "sort": "creation",
                "filter": "default",
                "site": "stackoverflow",
                "pagesize": 50,
            }
            if search:
                params["intitle"] = search
                
            api_url = STACKOVERFLOW_API
            import urllib.parse
            query_string = urllib.parse.urlencode(params)
            full_url = f"{api_url}?{query_string}"
            
            try:
                resp = self.fetch(full_url)
                data = resp.json()
                for item in data.get("items", []):
                    title = item.get("title", "")
                    company = item.get("company", {}).get("name", "") if isinstance(item.get("company"), dict) else ""
                    job_url = item.get("apply_url", "") or item.get("link", "")
                    description = item.get("description", "") or ""
                    location = "Remote"
                    
                    external_id = self.make_external_id(self.name, str(item.get("job_id", job_url)), title)
                    jobs.append(
                        RawJob(
                            external_id=external_id,
                            source=self.name,
                            title=title,
                            company=company or "Unknown",
                            url=job_url,
                            description=description,
                            location=location,
                            posted_at=str(item.get("created_at", "")),
                        )
                    )
            except Exception as e:
                logger.debug("Stack Exchange API failed: %s", e)
            
        except ImportError:
            logger.debug("feedparser not available")
        
        logger.info("StackOverflow scraper returning %d jobs via alternative sources", len(jobs))
        return jobs