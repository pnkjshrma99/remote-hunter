"""Workable public API scraper.

Workable provides a public JSON API endpoint per company subdomain.
No authentication required for reading public postings.
"""

import logging
from typing import Dict, List

import httpx

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

KNOWN_COMPANIES: Dict[str, str] = {
    "intercom": "Intercom",
    "coursera": "Coursera",
    "canva": "Canva",
    "wistia": "Wistia",
    "audible": "Audible",
    "grammarly": "Grammarly",
    "hotjar": "Hotjar",
    "lattice": "Lattice",
    "typeform": "Typeform",
    "webflow": "Webflow",
}


class WorkableScraper(BaseScraper):
    """Workable ATS public API scraper."""

    name = "workable"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        seen_ids: set = set()

        for slug, display_name in KNOWN_COMPANIES.items():
            url = f"https://apply.workable.com/{slug}/api/v1/jobs"
            try:
                with httpx.Client(timeout=10, follow_redirects=True) as client:
                    resp = client.get(url)
                if resp.status_code != 200:
                    logger.debug("Workable '%s' returned %s", slug, resp.status_code)
                    continue
                data = resp.json()
            except Exception as e:
                logger.debug("Workable '%s' error: %s", slug, e)
                continue

            for item in data.get("jobs", []):
                title = (item.get("title") or "").strip()
                if not title:
                    continue

                job_id = str(item.get("id", ""))
                ext_id = self.make_external_id(self.name, f"{slug}-{job_id}", title)
                if ext_id in seen_ids:
                    continue
                seen_ids.add(ext_id)

                jobs.append(
                    RawJob(
                        external_id=ext_id,
                        source=f"{self.name}:{slug}",
                        title=title,
                        company=display_name,
                        url=item.get("url", ""),
                        description=item.get("description", "") or "",
                        location=item.get("location", {}).get("city", ""),
                        posted_at=item.get("published_on", "") or item.get("created_at", ""),
                    )
                )

        logger.info("Workable: %d jobs from %d companies", len(jobs), len(KNOWN_COMPANIES))
        return jobs
