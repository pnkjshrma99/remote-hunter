"""Arbeitnow public API scraper."""

import logging
from typing import List

from scrapers.base import AuthRequiredError, BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

ARBEITNOW_API = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowScraper(BaseScraper):
    name = "arbeitnow"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: list[RawJob] = []
        try:
            response = self.fetch(ARBEITNOW_API)
            data = response.json()
        except AuthRequiredError:
            logger.warning("Arbeitnow API requires authentication")
            return []
        except Exception as exc:
            logger.warning("Arbeitnow fetch failed: %s", exc)
            return []

        for item in data.get("data", []):
            title = item.get("title", "")
            company = item.get("company_name", "") or "Unknown"
            job_url = item.get("url", "")
            tags = " ".join(item.get("tags", []) or [])
            description = f"{item.get('description', '')} {tags}"
            location = item.get("location", "") or ("Remote" if item.get("remote") else "")
            posted_at = ""
            if item.get("created_at"):
                posted_at = str(item["created_at"])

            jobs.append(
                RawJob(
                    external_id=self.make_external_id(self.name, job_url, title),
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
