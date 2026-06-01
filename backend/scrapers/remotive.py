"""Remotive public API scraper."""

import logging
from datetime import datetime
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

REMOTIVE_API = "https://remotive.com/api/remote-jobs"
DEVOPS_CATEGORY = "devops-sysadmin"
MAX_PAGES = 10


class RemotiveScraper(BaseScraper):
    name = "remotive"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        seen_ids: set = set()

        # Use source-side filtering
        params = self.get_source_params(criteria)
        search = params.get("query", "")

        # Build base URLs with source-side filtering
        if search:
            urls = [f"{REMOTIVE_API}?search={search.replace(' ', '%20')}"]
        else:
            urls = [REMOTIVE_API, f"{REMOTIVE_API}?category={DEVOPS_CATEGORY}"]

        # Add location filter if specified
        if params.get("location"):
            urls = [f"{url}&location={params['location'].replace(' ', '%20')}" for url in urls]

        for base_url in urls:
            for page in range(1, MAX_PAGES + 1):
                url = f"{base_url}&page={page}" if page > 1 else base_url
                try:
                    resp = self.fetch(url)
                    data = resp.json()
                except Exception as e:
                    logger.warning("Remotive fetch failed for %s: %s", url, e)
                    break

                items = data.get("jobs", [])
                if not items:
                    break  # no more pages

                for item in items:
                    title = item.get("title", "")
                    company = item.get("company_name", "")
                    job_url = item.get("url", "")
                    description = item.get("description", "") or ""
                    location = item.get("candidate_required_location", "") or ""
                    salary = item.get("salary", "") or ""

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
                            salary=salary,
                            posted_at=item.get("publication_date"),
                        )
                    )

        return jobs
