"""Career Nest public API scraper - 9K+ jobs, no auth needed."""

import logging
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

API_BASE = "https://careernest.cloud/api/feed"
MAX_PAGES = 10


class CareerNestScraper(BaseScraper):
    name = "careernest"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        seen_ids: set = set()

        for page in range(1, MAX_PAGES + 1):
            url = f"{API_BASE}?page={page}&limit=50"

            try:
                resp = self.fetch(url)
                data = resp.json()
            except Exception as e:
                logger.warning("Career Nest page %d failed: %s", page, e)
                break

            items = data.get("jobs", [])
            if not items:
                break

            for item in items:
                title = item.get("title", "")
                company = item.get("company", "Unknown")
                job_url = item.get("apply_url") or item.get("job_url", "")
                location = item.get("location", "Remote") or "Remote"
                salary = item.get("salary") or ""
                job_type = item.get("job_type", "")
                category = item.get("category", "")
                raw_desc = item.get("description", "") or ""
                posted_at = item.get("posted_at", "") or ""

                tags = [t for t in [category, job_type] if t]
                description = raw_desc
                if tags:
                    description += f" Tags: {', '.join(tags)}"

                external_id = self.make_external_id(self.name, job_url, title)
                if external_id in seen_ids:
                    continue
                seen_ids.add(external_id)

                jobs.append(
                    RawJob(
                        external_id=external_id,
                        source=self.name,
                        title=title,
                        company=company,
                        url=job_url,
                        description=description,
                        location=location,
                        salary=str(salary) if salary else "",
                        posted_at=posted_at,
                    )
                )

            logger.info(
                "Career Nest page %d: %d items (total: %s)",
                page, len(items), data.get("total", "?"),
            )

        logger.info("Fetched %d jobs from Career Nest", len(jobs))
        return jobs
