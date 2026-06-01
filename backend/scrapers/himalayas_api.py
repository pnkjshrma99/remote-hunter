"""Himalayas.app public API scraper.

Uses the Himalayas public API which returns 107K+ remote jobs
with structured data (salary, location, company, seniority, etc.).
"""

import logging
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

HIMALAYAS_API = "https://himalayas.app/jobs/api"
MAX_PAGES = 10


class HimalayasAPIScraper(BaseScraper):
    """Himalayas.app API scraper — 107K+ remote jobs with rich data."""

    name = "himalayas_api"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        seen_ids: set = set()

        for page in range(0, MAX_PAGES):
            url = f"{HIMALAYAS_API}?offset={page * 20}&limit=20"
            if criteria and criteria.query:
                url += f"&query={criteria.query.replace(' ', '%20')}"

            try:
                resp = self.fetch(url)
                data = resp.json()
            except Exception as e:
                logger.warning("Himalayas API fetch failed (page %d): %s", page, e)
                break

            items = data.get("jobs", [])
            if not items:
                break

            for item in items:
                title = item.get("title", "")
                company = item.get("companyName", "") or "Unknown"
                job_url = item.get("url", "")
                description = item.get("excerpt", "") or ""
                tags = item.get("tags", [])
                if tags:
                    description += f" Tags: {', '.join(tags)}"

                # Location: city, country
                location_parts = []
                if item.get("city"):
                    location_parts.append(item["city"])
                if item.get("country"):
                    location_parts.append(item["country"])
                location = ", ".join(location_parts) if location_parts else "Remote"

                # Salary
                salary = ""
                min_sal = item.get("minSalary")
                max_sal = item.get("maxSalary")
                currency = item.get("currency", "USD")
                if min_sal and max_sal:
                    salary = f"{currency} {min_sal} - {max_sal}"
                elif min_sal:
                    salary = f"{currency} {min_sal}+"

                posted_at = item.get("createdAt", "")

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
                        posted_at=str(posted_at) if posted_at else "",
                    )
                )

        logger.info("Fetched %d jobs from Himalayas API", len(jobs))
        return jobs
