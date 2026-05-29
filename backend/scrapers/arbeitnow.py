"""Arbeitnow public API scraper."""

import logging
from typing import List

from scrapers.base import AuthRequiredError, BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

ARBEITNOW_API = "https://www.arbeitnow.com/api/job-board-api"
MAX_PAGES = 5


class ArbeitnowScraper(BaseScraper):
    name = "arbeitnow"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: list[RawJob] = []
        seen_ids: set = set()

        for page in range(1, MAX_PAGES + 1):
            url = f"{ARBEITNOW_API}?page={page}"
            try:
                response = self.fetch(url)
                data = response.json()
            except AuthRequiredError:
                logger.warning("Arbeitnow API requires authentication")
                return jobs
            except Exception as exc:
                logger.warning("Arbeitnow fetch failed (page %d): %s", page, exc)
                break

            items = data.get("data", [])
            if not items:
                break

            for item in items:
                title = item.get("title", "")
                company = item.get("company_name", "") or "Unknown"
                job_url = item.get("url", "")
                tags = " ".join(item.get("tags", []) or [])
                description = f"{item.get('description', '')} {tags}"
                location = item.get("location", "") or ("Remote" if item.get("remote") else "")
                posted_at = str(item["created_at"]) if item.get("created_at") else ""

                ext_id = self.make_external_id(self.name, job_url, title)
                if ext_id in seen_ids:
                    continue
                seen_ids.add(ext_id)
                jobs.append(
                    RawJob(
                        external_id=ext_id,
                        source=self.name,
                        title=title,
                        company=company,
                        url=job_url,
                        description=description,
                        location=location,
                        posted_at=posted_at,
                    )
                )

        return jobs
