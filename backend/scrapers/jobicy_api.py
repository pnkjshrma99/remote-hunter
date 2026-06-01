"""Jobicy API v2 scraper — remote jobs with rich data, no auth required."""

import logging
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

JOBICY_API = "https://jobicy.com/api/v2/remote-jobs"


class JobicyAPIScraper(BaseScraper):
    """Jobicy API v2 scraper — 50 remote jobs per run with industry, geo, level."""

    name = "jobicy"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        seen_ids: set = set()

        url = f"{JOBICY_API}?count=50"

        try:
            resp = self.fetch(url)
            data = resp.json()
        except Exception as e:
            logger.warning("Jobicy API fetch failed: %s", e)
            return []

        items = data.get("jobs", [])
        if not items:
            return []

        for item in items:
            title = item.get("jobTitle", "").strip()
            if not title:
                continue

            company = item.get("companyName", "") or "Unknown"
            job_url = item.get("url", "")

            location = item.get("jobGeo", "") or "Remote"
            industries = item.get("jobIndustry", [])
            job_types = item.get("jobType", [])
            level = item.get("jobLevel", "")

            description = item.get("jobDescription", "") or item.get("jobExcerpt", "") or ""
            tags = [t for t in [level] + industries + job_types if t]
            if tags:
                if description:
                    description += f"\nTags: {', '.join(tags)}"
                else:
                    description = f"Tags: {', '.join(tags)}"

            posted_at = ""

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
                    posted_at=posted_at,
                )
            )

        logger.info("Fetched %d jobs from Jobicy API", len(jobs))
        return jobs
