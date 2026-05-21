"""AngelList (Wellfound) jobs scraper for startup positions."""

import logging
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

ANGELLIST_API = "https://api.wellfound.com/graphql"


class AngelListScraper(BaseScraper):
    name = "angellist"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape AngelList (Wellfound) jobs - requires GraphQL."""
        jobs: List[RawJob] = []
        search = (criteria.query if criteria else "").strip()

        # AngelList primarily uses GraphQL, which requires authentication
        # Fallback to RSS if available
        try:
            # Try RSS endpoint as fallback
            rss_url = "https://angel.co/opportunities.rss"
            resp = self.fetch(rss_url)

            import feedparser
            feed = feedparser.parse(resp.text)

            for entry in feed.entries:
                title = entry.get("title", "")
                company = entry.get("author", "")
                job_url = entry.get("link", "")
                description = entry.get("summary", "") or ""
                location = "Remote"
                salary = ""

                external_id = self.make_external_id(self.name, job_url, title)
                jobs.append(
                    RawJob(
                        external_id=external_id,
                        source=self.name,
                        title=title,
                        company=company,
                        url=job_url,
                        description=description,
                        location=location,
                        salary=salary,
                        posted_at=entry.get("published"),
                    )
                )
        except Exception as e:
            logger.warning("AngelList fetch failed: %s", e)
            return []

        # Deduplicate
        seen = set()
        unique = []
        for j in jobs:
            if j.external_id not in seen:
                seen.add(j.external_id)
                unique.append(j)
        return unique
