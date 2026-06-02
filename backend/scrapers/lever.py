"""Lever public API scraper.

Lever provides a public JSON API endpoint per company.
No authentication required for reading public postings.
"""

import logging
from typing import Dict, List

import httpx

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

KNOWN_COMPANIES: Dict[str, str] = {
    "spotify": "Spotify",
    "stripe": "Stripe",
    "dropbox": "Dropbox",
    "asana": "Asana",
    "eventbrite": "Eventbrite",
    "huge": "Huge",
    "guru": "Guru",
    "n26": "N26",
    "upwork": "Upwork",
    "box": "Box",
    "coinbase": "Coinbase",
    "doordash": "DoorDash",
    "etsy": "Etsy",
    "github": "GitHub",
    "gitlab": "GitLab",
    "godaddy": "GoDaddy",
    "indeed": "Indeed",
    "kickstarter": "Kickstarter",
    "lyft": "Lyft",
    "medium": "Medium",
    "opencollective": "Open Collective",
    "pagerduty": "PagerDuty",
    "pinterest": "Pinterest",
    "quora": "Quora",
    "recurly": "Recurly",
    "slack": "Slack",
    "square": "Square",
    "uber": "Uber",
    "wework": "WeWork",
    "youtube": "YouTube",
}


class LeverScraper(BaseScraper):
    """Lever ATS public API scraper."""

    name = "lever"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        seen_ids: set = set()

        for slug, display_name in KNOWN_COMPANIES.items():
            url = f"https://api.lever.co/v1/postings/{slug}?mode=json"
            try:
                with httpx.Client(timeout=10, follow_redirects=True) as client:
                    resp = client.get(url)
                if resp.status_code != 200:
                    logger.debug("Lever '%s' returned %s", slug, resp.status_code)
                    continue
                data = resp.json()
            except Exception as e:
                logger.debug("Lever '%s' error: %s", slug, e)
                continue

            for item in data if isinstance(data, list) else data.get("data", []):
                title = (item.get("text") or item.get("title", "")).strip()
                if not title:
                    continue

                job_id = str(item.get("id", ""))
                ext_id = self.make_external_id(self.name, f"{slug}-{job_id}", title)
                if ext_id in seen_ids:
                    continue
                seen_ids.add(ext_id)

                categories = item.get("categories", {}) or {}
                location = categories.get("location", "") or item.get("location", "")
                description = (item.get("description") or item.get("descriptionPlain", "") or "")
                if isinstance(description, dict):
                    description = description.get("text", "") or description.get("plain", "") or ""

                jobs.append(
                    RawJob(
                        external_id=ext_id,
                        source=f"{self.name}:{slug}",
                        title=title,
                        company=display_name,
                        url=item.get("hostedUrl", "") or item.get("url", ""),
                        description=description,
                        location=location or "Remote",
                        posted_at=item.get("createdAt", "") or item.get("updatedAt", ""),
                    )
                )

        logger.info("Lever: %d jobs from %d companies", len(jobs), len(KNOWN_COMPANIES))
        return jobs
