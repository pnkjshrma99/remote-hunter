"""Dev.to Jobs Scraper

Fetches jobs from Dev.to API using the articles endpoint with tag=jobs.
"""

import logging
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)


class DevToScraper(BaseScraper):
    """Dev.to API scraper — fetches tagged job articles."""

    name = "devto"
    BASE_URL = "https://dev.to/api"
    MAX_PAGES = 3

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        seen_ids: set = set()

        for page in range(1, self.MAX_PAGES + 1):
            url = f"{self.BASE_URL}/articles?tag=jobs&per_page=50&page={page}"

            try:
                resp = self.fetch(url)
                data = resp.json()
            except Exception as e:
                logger.warning("Dev.to API page %d failed: %s", page, e)
                break

            if not isinstance(data, list) or not data:
                break

            for item in data:
                title = item.get("title", "").strip()
                if not title:
                    continue

                url_value = item.get("url", "")
                if not url_value:
                    continue

                org = item.get("organization", {}) or {}
                user = item.get("user", {}) or {}
                company = org.get("name", "") or user.get("username", "") or "Dev.to"

                description = item.get("description", "") or ""
                tags = item.get("tag_list", []) or item.get("tags", [])
                if tags and not description:
                    description = f"Tags: {', '.join(tags)}"

                location = "Remote"
                if tags:
                    for t in tags:
                        t_lower = t.lower()
                        if "remote" in t_lower or "worldwide" in t_lower:
                            location = "Remote"
                            break

                posted_at = item.get("published_at", "") or item.get("created_at", "")

                external_id = self.make_external_id(self.name, url_value, title)
                if external_id in seen_ids:
                    continue
                seen_ids.add(external_id)

                jobs.append(RawJob(
                    external_id=external_id,
                    source=self.name,
                    title=title,
                    company=company,
                    url=url_value,
                    description=description,
                    location=location,
                    posted_at=str(posted_at) if posted_at else "",
                ))

            logger.info("Dev.to page %d: %d items", page, len(data))

        logger.info("Fetched %d jobs from Dev.to", len(jobs))
        return jobs
