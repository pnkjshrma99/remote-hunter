"""RemoteJobs.org public API scraper - 10K+ remote jobs, no auth needed."""

import logging
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

API_BASE = "https://remotejobs.org/api/v1/jobs"
MAX_PAGES = 15


class RemoteJobsOrgScraper(BaseScraper):
    name = "remotejobs_org"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        seen_ids: set = set()

        for page in range(MAX_PAGES):
            offset = page * 50
            url = f"{API_BASE}?limit=50&offset={offset}"
            if criteria and criteria.query:
                url += f"&q={criteria.query.replace(' ', '%20')}"

            try:
                resp = self.fetch(url)
                data = resp.json()
            except Exception as e:
                logger.warning("RemoteJobs.org page %d failed: %s", page, e)
                break

            items = data.get("data", [])
            if not items:
                break

            for item in items:
                title = item.get("title", "")
                company = item.get("company", {}).get("name", "Unknown")
                job_url = item.get("apply_url") or item.get("url", "")
                location = item.get("location", "Remote") or "Remote"
                salary_text = item.get("salary_text") or ""
                job_type = item.get("type", "")
                description = item.get("description", "") or ""
                category = item.get("category", {}).get("name", "")
                posted_at = item.get("posted_at", "") or ""

                tags = [t for t in [category, job_type] if t]
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
                        salary=salary_text,
                        posted_at=posted_at,
                    )
                )

            total = data.get("pagination", {}).get("total", 0)
            logger.info(
                "RemoteJobs.org page %d: %d items (total avail: %d)",
                page + 1, len(items), total,
            )

        logger.info("Fetched %d jobs from RemoteJobs.org", len(jobs))
        return jobs
