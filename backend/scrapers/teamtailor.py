"""TeamTailor public API scraper.

TeamTailor provides a public JSON API endpoint per company.
No authentication required for reading public jobs.
"""

import logging
from typing import Dict, List

import httpx

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

KNOWN_COMPANIES: Dict[str, str] = {
    "klarna": "Klarna",
    "klarasystems": "Klara Systems",
    "afosto": "Afosto",
    "reedsy": "Reedsy",
    "mentimeter": "Mentimeter",
    "northvolt": "Northvolt",
    "paga": "Paga",
    "pleo": "Pleo",
    "truesec": "Truesec",
    "veriff": "Veriff",
}


class TeamTailorScraper(BaseScraper):
    """TeamTailor ATS public API scraper."""

    name = "teamtailor"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        seen_ids: set = set()

        for slug, display_name in KNOWN_COMPANIES.items():
            url = f"https://{slug}.teamtailor.com/api/v1/jobs"
            try:
                with httpx.Client(timeout=10, follow_redirects=True) as client:
                    resp = client.get(url)
                if resp.status_code != 200:
                    logger.debug("TeamTailor '%s' returned %s", slug, resp.status_code)
                    continue
                data = resp.json()
            except Exception as e:
                logger.debug("TeamTailor '%s' error: %s", slug, e)
                continue

            items = data.get("data", [])
            for item in items:
                attrs = item.get("attributes", {}) or {}
                title = (attrs.get("title", "") or "").strip()
                if not title:
                    continue

                job_id = str(item.get("id", ""))
                ext_id = self.make_external_id(self.name, f"{slug}-{job_id}", title)
                if ext_id in seen_ids:
                    continue
                seen_ids.add(ext_id)

                description = (attrs.get("description", "") or attrs.get("body", "") or "")
                location = (attrs.get("location", "") or attrs.get("city", "") or "Remote")

                jobs.append(
                    RawJob(
                        external_id=ext_id,
                        source=f"{self.name}:{slug}",
                        title=title,
                        company=display_name,
                        url=attrs.get("url", "") or attrs.get("apply_url", ""),
                        description=description,
                        location=location,
                        posted_at=attrs.get("published_at", "") or attrs.get("created_at", ""),
                    )
                )

        logger.info("TeamTailor: %d jobs from %d companies", len(jobs), len(KNOWN_COMPANIES))
        return jobs
