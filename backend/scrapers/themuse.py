"""The Muse public API scraper — 8K+ remote jobs, no auth required."""

import logging
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

MUSE_API = "https://www.themuse.com/api/public/jobs"
MAX_PAGES = 10


class MuseScraper(BaseScraper):
    """The Muse public API scraper — 8K+ remote jobs across all categories."""

    name = "themuse"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        seen_ids: set = set()

        for page in range(1, MAX_PAGES + 1):
            url = f"{MUSE_API}?page={page}&location=Remote&descending=true"
            if criteria and criteria.query:
                url += f"&query={criteria.query.replace(' ', '%20')}"

            try:
                resp = self.fetch(url)
                data = resp.json()
            except Exception as e:
                logger.warning("Muse API page %d failed: %s", page, e)
                break

            results = data.get("results", [])
            if not results:
                break

            for item in results:
                title = item.get("name", "").strip()
                if not title:
                    continue

                company = item.get("company", {}).get("name", "Unknown")

                # Location
                locations = item.get("locations", [])
                location = "Remote"
                if locations:
                    loc_names = [l.get("name", "") for l in locations if l.get("name")]
                    if loc_names:
                        location = ", ".join(loc_names)

                # URL
                job_url = item.get("refs", {}).get("landing_page", "")

                # Description
                description = item.get("contents", "") or ""

                # Add category/level info
                categories = item.get("categories", [])
                levels = item.get("levels", [])
                tags = []
                if categories:
                    tags.extend(c.get("name", "") for c in categories if c.get("name"))
                if levels:
                    tags.extend(l.get("name", "") for l in levels if l.get("name"))
                if tags:
                    if description:
                        description += f"\nTags: {', '.join(tags)}"
                    else:
                        description = f"Tags: {', '.join(tags)}"

                posted_at = item.get("publication_date", "")

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
                        salary="",
                        posted_at=str(posted_at) if posted_at else "",
                    )
                )

        logger.info("Fetched %d jobs from The Muse API", len(jobs))
        return jobs
