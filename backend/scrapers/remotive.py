"""Remotive public API scraper."""

import logging
from datetime import datetime
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

REMOTIVE_API = "https://remotive.com/api/remote-jobs"
DEVOPS_CATEGORY = "devops-sysadmin"


class RemotiveScraper(BaseScraper):
    name = "remotive"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        
        # Use source-side filtering
        params = self.get_source_params(criteria)
        search = params.get("query", "")
        
        # Build URLs with source-side filtering
        urls = [REMOTIVE_API, f"{REMOTIVE_API}?category={DEVOPS_CATEGORY}"]
        if search:
            urls.insert(0, f"{REMOTIVE_API}?search={search.replace(' ', '%20')}")
        
        # Add location filter if specified
        if params.get("location"):
            urls = [f"{url}&location={params['location'].replace(' ', '%20')}" for url in urls]
        for url in urls:
            try:
                resp = self.fetch(url)
                data = resp.json()
            except Exception as e:
                logger.warning("Remotive fetch failed for %s: %s", url, e)
                continue

            for item in data.get("jobs", []):
                title = item.get("title", "")
                company = item.get("company_name", "")
                job_url = item.get("url", "")
                description = item.get("description", "") or ""
                location = item.get("candidate_required_location", "") or ""
                salary = item.get("salary", "") or ""

                external_id = self.make_external_id(self.name, job_url, title)
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
                        posted_at=item.get("publication_date"),
                    )
                )

        # Deduplicate within batch
        seen = set()
        unique = []
        for j in jobs:
            if j.external_id not in seen:
                seen.add(j.external_id)
                unique.append(j)
        return unique
