"""Greenhouse public job board API scraper."""

import logging
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Default boards known for remote hiring (extensible via env)
DEFAULT_BOARDS = [
    "gitlab",
    "hashicorp",
    "datadog",
    "grafana",
    "cloudflare",
]


class GreenhouseScraper(BaseScraper):
    name = "greenhouse"

    def __init__(self, board_tokens: List[str] | None = None):
        super().__init__()
        tokens = board_tokens or settings.greenhouse_tokens_list or DEFAULT_BOARDS
        self.board_tokens = tokens

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        for token in self.board_tokens:
            url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
            try:
                resp = self.fetch(url)
                data = resp.json()
            except Exception as e:
                logger.warning("Greenhouse board %s failed: %s", token, e)
                continue

            for item in data.get("jobs", []):
                title = item.get("title", "")
                company = token.replace("-", " ").title()
                job_url = item.get("absolute_url", "")
                location = ""
                offices = item.get("offices", [])
                if offices:
                    location = ", ".join(o.get("name", "") for o in offices)
                departments = item.get("departments", [])
                dept_names = ", ".join(d.get("name", "") for d in departments)
                description = f"{dept_names} {location}"

                external_id = self.make_external_id(
                    self.name, str(item.get("id", job_url)), title
                )
                jobs.append(
                    RawJob(
                        external_id=external_id,
                        source=f"{self.name}:{token}",
                        title=title,
                        company=company,
                        url=job_url,
                        description=description,
                        location=location or "See job posting",
                        posted_at=item.get("updated_at"),
                    )
                )
        return jobs
