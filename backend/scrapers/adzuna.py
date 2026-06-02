"""Adzuna Jobs API scraper.

Adzuna provides a free-tier API (250 requests/month) that aggregates
jobs from thousands of sources across 10+ countries.
Requires free registration at https://developer.adzuna.com.
"""

import logging
from typing import List

import httpx

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

ADZUNA_API = "https://api.adzuna.com/v1/api/jobs"
COUNTRIES = ["gb", "us", "ca", "au", "de", "fr", "nl", "in"]


class AdzunaScraper(BaseScraper):
    """Adzuna Jobs API scraper — requires free API key.

    Register at https://developer.adzuna.com to get app_id and app_key.
    Set ADZUNA_APP_ID and ADZUNA_APP_KEY env vars.
    """

    name = "adzuna"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        app_id = settings.adzuna_app_id or ""
        app_key = settings.adzuna_app_key or ""

        if not app_id or not app_key:
            logger.warning("AdzunaScraper: ADZUNA_APP_ID and ADZUNA_APP_KEY not set")
            return []

        query = (criteria and criteria.query) or "DevOps Engineer"
        jobs: List[RawJob] = []
        seen_ids: set = set()

        for country in COUNTRIES:
            params = {
                "app_id": app_id,
                "app_key": app_key,
                "results_per_page": 50,
                "what": query,
                "where": "remote",
                "content_type": "application/json",
                "max_days_old": (criteria and criteria.posted_within_days) or 14,
            }
            url = f"{ADZUNA_API}/{country}/search/1"

            try:
                with httpx.Client(timeout=10) as client:
                    resp = client.get(url, params=params)
                if resp.status_code != 200:
                    logger.debug("Adzuna %s returned %s", country, resp.status_code)
                    continue
                data = resp.json()
            except Exception as e:
                logger.debug("Adzuna %s error: %s", country, e)
                continue

            for item in data.get("results", []):
                title = (item.get("title") or "").strip()
                if not title:
                    continue

                job_id = str(item.get("id", ""))
                ext_id = self.make_external_id(self.name, f"{country}-{job_id}", title)
                if ext_id in seen_ids:
                    continue
                seen_ids.add(ext_id)

                company = (item.get("company", {}) or {}).get("display_name", "") or ""
                if not company:
                    company = item.get("company_name", "")

                location = item.get("location", {}).get("display_name", "") if isinstance(item.get("location"), dict) else str(item.get("location", ""))
                description = item.get("description", "") or ""
                url = item.get("redirect_url", "") or item.get("url", "")

                salary_min = item.get("salary_min")
                salary_max = item.get("salary_max")
                salary_str = ""
                if salary_min and salary_max:
                    salary_str = f"${int(salary_min)}-${int(salary_max)}"
                elif salary_min:
                    salary_str = f"${int(salary_min)}+"

                jobs.append(
                    RawJob(
                        external_id=ext_id,
                        source=f"{self.name}:{country}",
                        title=title,
                        company=company,
                        url=url,
                        description=description,
                        location=location or "Remote",
                        posted_at=item.get("created", "") or "",
                        salary=salary_str,
                    )
                )

        logger.info("Adzuna: %d jobs from %d countries", len(jobs), len(COUNTRIES))
        return jobs
