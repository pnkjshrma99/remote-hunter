"""Stack Overflow Jobs scraper - targets remote positions."""

import logging
from typing import List
from datetime import datetime

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

STACKOVERFLOW_API = "https://stackoverflow.com/jobs/feed"


class StackOverflowScraper(BaseScraper):
    name = "stackoverflow"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape Stack Overflow jobs RSS feed."""
        jobs: List[RawJob] = []
        search = (criteria.query if criteria else "").strip().replace(" ", "%20")

        # StackOverflow Jobs feed with remote filter
        urls = [
            f"{STACKOVERFLOW_API}?q=remote&pg=1",
            f"{STACKOVERFLOW_API}?q=remote+{search}&pg=1" if search else None,
        ]
        urls = [u for u in urls if u]

        try:
            import feedparser

            for url in urls:
                try:
                    feed = feedparser.parse(url)
                    for entry in feed.entries[:50]:  # Limit to 50 per page
                        title = entry.get("title", "")
                        company = entry.get("author", "")
                        job_url = entry.get("link", "")
                        description = entry.get("summary", "") or ""
                        location = "Remote"
                        salary = ""

                        # Try to extract salary from description
                        if "$" in description or "£" in description or "€" in description:
                            import re
                            salary_match = re.search(r'[\$£€][\d,]+', description)
                            if salary_match:
                                salary = salary_match.group()

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
                    logger.warning("StackOverflow fetch failed for %s: %s", url, e)
                    continue

        except ImportError:
            logger.warning("feedparser not installed - skipping Stack Overflow scraper")
            return []

        # Deduplicate
        seen = set()
        unique = []
        for j in jobs:
            if j.external_id not in seen:
                seen.add(j.external_id)
                unique.append(j)
        return unique
