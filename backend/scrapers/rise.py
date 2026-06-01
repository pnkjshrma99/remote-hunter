"""Rise (JoinRise) public API scraper - jobs with salary data."""

import logging
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

API_BASE = "https://api.joinrise.io/api/v1/jobs/public"
MAX_PAGES = 5


class RiseScraper(BaseScraper):
    name = "rise"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        seen_ids: set = set()

        for page in range(1, MAX_PAGES + 1):
            url = f"{API_BASE}?page={page}&limit=20&includeDescription=false"

            try:
                resp = self.fetch(url)
                data = resp.json()
            except Exception as e:
                logger.warning("Rise API page %d failed: %s", page, e)
                break

            items = data.get("result", {}).get("jobs", [])
            if not items:
                break

            for item in items:
                title = item.get("title", "")
                owner = item.get("owner", {}) or {}
                company = owner.get("companyName", "Unknown")
                job_url = item.get("url", "")
                location = item.get("location", {}).get("address", "Remote") or "Remote"
                if location in ("No location specified", ""):
                    location = "Remote"
                desc = item.get("descriptionBreakdown", {}) or {}
                salary_min = desc.get("salaryRangeMinYearly")
                salary_max = desc.get("salaryRangeMaxYearly")
                salary = ""
                if salary_min and salary_max:
                    salary = f"${salary_min} - ${salary_max}/yr"
                elif salary_min:
                    salary = f"${salary_min}+/yr"
                posted_at = item.get("createdAt", "") or ""
                emp_type = desc.get("employmentType", "")
                work_model = desc.get("workModel", "")
                seniority = item.get("seniority", "")

                tags = [t for t in [emp_type, work_model, seniority] if t]
                description = f"{title} at {company}"
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
                        salary=salary,
                        posted_at=posted_at,
                    )
                )

            logger.info("Rise page %d: %d items", page, len(items))

        logger.info("Fetched %d jobs from Rise API", len(jobs))
        return jobs
