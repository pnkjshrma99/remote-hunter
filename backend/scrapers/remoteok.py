"""Remote OK API scraper."""

import logging
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

REMOTEOK_API = "https://remoteok.com/api"


class RemoteOKScraper(BaseScraper):
    name = "remoteok"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        try:
            resp = self.fetch(REMOTEOK_API)
            data = resp.json()
        except Exception as e:
            logger.warning("RemoteOK fetch failed: %s", e)
            return []

        if not isinstance(data, list):
            return []

        for item in data:
            if not isinstance(item, dict) or "position" not in item:
                continue
            title = item.get("position", "")
            company = item.get("company", "")
            job_url = item.get("url", "") or f"https://remoteok.com/remote-jobs/{item.get('id', '')}"
            tags = " ".join(item.get("tags", []) or [])
            description = item.get("description", "") or tags
            location = item.get("location", "") or "Worldwide"

            external_id = self.make_external_id(self.name, str(item.get("id", job_url)), title)
            jobs.append(
                RawJob(
                    external_id=external_id,
                    source=self.name,
                    title=title,
                    company=company,
                    url=job_url,
                    description=description,
                    location=location,
                    salary=item.get("salary", "") or "",
                    posted_at=item.get("date"),
                )
            )
        return jobs
