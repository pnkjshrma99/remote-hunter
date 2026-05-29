"""Remote OK API scraper."""

import logging
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

REMOTEOK_API = "https://remoteok.com/api"
MAX_PAGES = 3


class RemoteOKScraper(BaseScraper):
    name = "remoteok"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        seen_ids: set = set()

        for page in range(1, MAX_PAGES + 1):
            url = f"{REMOTEOK_API}?page={page}" if page > 1 else REMOTEOK_API
            try:
                resp = self.fetch(url)
                data = resp.json()
            except Exception as e:
                logger.warning("RemoteOK fetch failed (page %d): %s", page, e)
                break

            if not isinstance(data, list):
                break

            found = 0
            for item in data:
                if not isinstance(item, dict) or "position" not in item:
                    continue
                title = item.get("position", "")
                company = item.get("company", "")
                job_url = item.get("url", "") or f"https://remoteok.com/remote-jobs/{item.get('id', '')}"
                tags = " ".join(item.get("tags", []) or [])
                description = item.get("description", "") or tags
                location = item.get("location", "") or "Worldwide"

                ext_id = self.make_external_id(self.name, str(item.get("id", job_url)), title)
                if ext_id in seen_ids:
                    continue
                seen_ids.add(ext_id)
                found += 1
                jobs.append(
                    RawJob(
                        external_id=ext_id,
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

            if found == 0:
                break  # no more results

        return jobs
