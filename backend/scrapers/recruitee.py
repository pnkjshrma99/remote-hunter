"""Recruitee public API scraper.

Recruitee provides a public JSON API endpoint per company.
No authentication required for reading public offers.
"""

import logging
from typing import Dict, List

import httpx

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

KNOWN_COMPANIES: Dict[str, str] = {
    "deliveroo": "Deliveroo",
    "transferwise": "Wise",
    "buffer": "Buffer",
    "automattic": "Automattic",
    "stripe": "Stripe",
    "zapier": "Zapier",
    "gitlab": "GitLab",
    "datadog": "Datadog",
    "digitalocean": "DigitalOcean",
    "doist": "Doist",
}


class RecruiteeScraper(BaseScraper):
    """Recruitee ATS public API scraper."""

    name = "recruitee"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        seen_ids: set = set()

        for slug, display_name in KNOWN_COMPANIES.items():
            url = f"https://{slug}.recruitee.com/api/offers"
            try:
                with httpx.Client(timeout=10, follow_redirects=True) as client:
                    resp = client.get(url)
                if resp.status_code != 200:
                    logger.debug("Recruitee '%s' returned %s", slug, resp.status_code)
                    continue
                data = resp.json()
            except Exception as e:
                logger.debug("Recruitee '%s' error: %s", slug, e)
                continue

            offers = data.get("offers", [])
            for item in offers:
                title = (item.get("title", "") or "").strip()
                if not title:
                    continue

                job_id = str(item.get("id", ""))
                ext_id = self.make_external_id(self.name, f"{slug}-{job_id}", title)
                if ext_id in seen_ids:
                    continue
                seen_ids.add(ext_id)

                description = (item.get("description", "") or item.get("description_html", "") or "")
                location = (item.get("location", "") or item.get("city", "") or "Remote")

                jobs.append(
                    RawJob(
                        external_id=ext_id,
                        source=f"{self.name}:{slug}",
                        title=title,
                        company=display_name,
                        url=item.get("url", "") or item.get("apply_url", ""),
                        description=description,
                        location=location,
                        posted_at=item.get("published_at", "") or item.get("created_at", ""),
                    )
                )

        logger.info("Recruitee: %d jobs from %d companies", len(jobs), len(KNOWN_COMPANIES))
        return jobs
