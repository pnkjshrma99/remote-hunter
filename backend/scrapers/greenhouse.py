"""Greenhouse public job board API scraper."""

import logging
from typing import List, Dict, Optional, Tuple
import concurrent.futures

import httpx

from scrapers.base import AuthRequiredError, BaseScraper
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

        # Optional parallel detail fetching to enrich descriptions (disabled by default)
        self.fetch_details: bool = bool(getattr(settings, "greenhouse_fetch_details", False))
        self.max_workers: int = int(getattr(settings, "greenhouse_max_workers", 10))

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []

        # Fetch all board listings FIRST (one request per board)
        board_data: Dict[str, dict] = {}
        for token in self.board_tokens:
            url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
            try:
                resp = self.fetch(url)
                board_data[token] = resp.json()
                logger.debug(
                    "Greenhouse %s: %d jobs in listing",
                    token,
                    len(board_data[token].get("jobs", [])),
                )
            except AuthRequiredError:
                logger.warning(f"Greenhouse board '{token}' requires auth")
                continue
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.warning(f"Greenhouse board '{token}' not found (404).")
                else:
                    logger.warning(f"Greenhouse board {token} failed: {e}")
                continue
            except Exception as e:
                logger.warning(f"Greenhouse board {token} failed: {e}")
                continue

        # If detail fetching is enabled, perform concurrent requests for job details
        detail_tasks: List[Tuple[str, dict]] = []
        for token, data in board_data.items():
            for item in data.get("jobs", []):
                detail_tasks.append((token, item))

        if self.fetch_details and detail_tasks:
            logger.info(
                "Greenhouse: fetching %d job details concurrently (max_workers=%d)",
                len(detail_tasks),
                self.max_workers,
            )

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_task = {
                    executor.submit(self._fetch_detail, token, item.get("id")): (token, item)
                    for token, item in detail_tasks
                }

                for fut in concurrent.futures.as_completed(future_to_task):
                    token, item = future_to_task[fut]
                    company = token.replace("-", " ").title()
                    try:
                        detail_json = fut.result()
                    except Exception:
                        detail_json = None

                    title = item.get("title", "")
                    job_url = item.get("absolute_url", "")
                    job_id = item.get("id")
                    offices = item.get("offices", [])
                    location = ", ".join(o.get("name", "") for o in offices) if offices else ""

                    # Prefer description from detail endpoint when available
                    description = ""
                    if detail_json:
                        # Common greenhouse detail keys
                        description = detail_json.get("content") or detail_json.get("description") or ""

                    # Fallback to department names
                    if not description:
                        departments = item.get("departments", [])
                        dept_names = ", ".join(d.get("name", "") for d in departments)
                        description = dept_names or ""

                    posted_at = item.get("updated_at", "")
                    external_id = self.make_external_id(self.name, str(job_id or job_url), title)

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
        else:
            # No detail fetching: build jobs from list endpoint
            for token, data in board_data.items():
                company = token.replace("-", " ").title()

                for item in data.get("jobs", []):
                    title = item.get("title", "")
                    job_url = item.get("absolute_url", "")
                    job_id = item.get("id")

                    offices = item.get("offices", [])
                    location = ", ".join(o.get("name", "") for o in offices) if offices else ""

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

        logger.info(
            "Greenhouse: %d jobs from %d boards (%s)",
            len(jobs),
            len(self.board_tokens),
            "detail fetches" if self.fetch_details else "no detail fetches",
        )
        return jobs

    def _fetch_detail(self, token: str, job_id: Optional[int]) -> Optional[dict]:
        if not job_id:
            return None
        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job_id}"
        try:
            resp = self.fetch(url)
            return resp.json()
        except Exception as e:
            logger.debug(f"Greenhouse detail fetch failed for {token}/{job_id}: {e}")
            return None
