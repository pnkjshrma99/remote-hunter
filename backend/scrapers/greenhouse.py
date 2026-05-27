"""Greenhouse public job board API scraper."""

import logging
from typing import List

import httpx

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Default boards known for remote hiring (extensible via env)
DEFAULT_BOARDS = [
    "gitlab",
    "datadog",
    "cloudflare",
    "grafanalabs",
]

COMMON_SLUG_MISTAKES = {
    "grafana": "grafanalabs",
    "hashicorp": None,
}


class GreenhouseScraper(BaseScraper):
    name = "greenhouse"

    def __init__(self, board_tokens: List[str] | None = None):
        super().__init__()
        tokens = board_tokens or settings.greenhouse_tokens_list or DEFAULT_BOARDS
        # Fix: replace common slug mistakes with correct slugs, don't filter them out
        self.board_tokens = [
            COMMON_SLUG_MISTAKES.get(t, t) for t in tokens
            if COMMON_SLUG_MISTAKES.get(t) is not None
        ]
        original_count = len(tokens)
        if len(self.board_tokens) != original_count:
            logger.warning(
                "Greenhouse: corrected %d board slug(s) (e.g. grafana->grafanalabs)",
                original_count - len(self.board_tokens)
            )

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        
        # Fetch all board listings FIRST (fast, one request per board)
        board_data = {}
        for token in self.board_tokens:
            url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
            try:
                resp = self.fetch(url)
                board_data[token] = resp.json()
                logger.debug(f"Greenhouse {token}: {len(board_data[token].get('jobs', []))} jobs in listing")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.warning(f"Greenhouse board '{token}' not found (404).")
                else:
                    logger.warning(f"Greenhouse board {token} failed: {e}")
                continue
            except Exception as e:
                logger.warning(f"Greenhouse board {token} failed: {e}")
                continue
        
        # Process listings - skip individual detail fetches to avoid
        # N additional HTTP requests per board (saves minutes of latency)
        for token, data in board_data.items():
            company = token.replace("-", " ").title()
            
            for item in data.get("jobs", []):
                title = item.get("title", "")
                job_url = item.get("absolute_url", "")
                job_id = item.get("id")
                
                # Extract location directly from the list response
                offices = item.get("offices", [])
                location = ", ".join(o.get("name", "") for o in offices) if offices else ""
                
                # Use data available in the list endpoint to avoid N+1 requests
                departments = item.get("departments", [])
                dept_names = ", ".join(d.get("name", "") for d in departments)
                
                description = f"{dept_names}" if dept_names else ""
                posted_at = item.get("updated_at", "")
                
                external_id = self.make_external_id(
                    self.name, str(job_id or job_url), title
                )
                jobs.append(
                    RawJob(
                        external_id=external_id,
                        source=f"{self.name}:{token}",
                        title=title,
                        company=company,
                        url=job_url,
                        description=description,
                        location=location or "Remote",
                        posted_at=posted_at,
                    )
                )
        
        logger.info(f"Greenhouse: {len(jobs)} jobs from {len(self.board_tokens)} boards (no detail fetches)")
        return jobs
