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

# Default boards — only companies with high likelihood of remote engineering roles
DEFAULT_BOARDS = [
    "gitlab", "datadog", "cloudflare", "grafanalabs", "automattic",
    "digitalocean", "zapier", "stripe", "doist", "buffer",
    "hashicorp", "supabase", "sentry", "vercel", "dropbox",
    "spotify", "confluent", "mongodb", "elastic", "fastly",
    "shopify", "snowflake", "coinbase", "discord", "notion",
]

COMMON_SLUG_MISTAKES = {
    "grafana": "grafanalabs",
}


class GreenhouseScraper(BaseScraper):
    name = "greenhouse"

    def __init__(self, board_tokens: List[str] | None = None):
        super().__init__()
        tokens = board_tokens or settings.greenhouse_tokens_list or DEFAULT_BOARDS
        # Fix: replace common slug mistakes with correct slugs
        self.board_tokens = [COMMON_SLUG_MISTAKES.get(t, t) for t in tokens]
        original_count = len(tokens)
        if len(self.board_tokens) != original_count:
            logger.warning(
                "Greenhouse: corrected %d board slug(s) (e.g. grafana->grafanalabs)",
                original_count - len(self.board_tokens)
            )

        # Disable by default — listing endpoint already has title/company/location.
        # Set GREENHOUSE_FETCH_DETAILS=true on Render if you need full descriptions.
        self.fetch_details: bool = bool(getattr(settings, "greenhouse_fetch_details", False))
        self.max_workers: int = int(getattr(settings, "greenhouse_max_workers", 5))

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []

        # Fetch all board listings in parallel
        board_data: Dict[str, dict] = {}

        def _fetch_board(token: str) -> Tuple[str, dict | None]:
            url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
            try:
                resp = self.fetch(url)
                data = resp.json()
                logger.debug(
                    "Greenhouse %s: %d jobs in listing",
                    token,
                    len(data.get("jobs", [])),
                )
                return token, data
            except AuthRequiredError:
                logger.warning(f"Greenhouse board '{token}' requires auth")
                return token, None
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.warning(f"Greenhouse board '{token}' not found (404).")
                else:
                    logger.warning(f"Greenhouse board {token} failed: {e}")
                return token, None
            except Exception as e:
                logger.warning(f"Greenhouse board {token} failed: {e}")
                return token, None

        board_workers = min(len(self.board_tokens), 20)
        with concurrent.futures.ThreadPoolExecutor(max_workers=board_workers) as ex:
            futures = {ex.submit(_fetch_board, t): t for t in self.board_tokens}
            for fut in concurrent.futures.as_completed(futures):
                token, data = fut.result()
                if data is not None:
                    board_data[token] = data

        # If detail fetching is enabled, perform concurrent requests for job details
        # Pre-filter by title keyword if criteria has a query
        query_keywords = []
        if criteria and criteria.query:
            query_keywords = [kw.lower() for kw in criteria.query.split()]

        detail_tasks: List[Tuple[str, dict]] = []
        for token, data in board_data.items():
            for item in data.get("jobs", []):
                title = item.get("title", "")
                if query_keywords:
                    title_lower = title.lower()
                    if not any(kw in title_lower for kw in query_keywords):
                        continue
                detail_tasks.append((token, item))

        if self.fetch_details and detail_tasks:
            logger.info(
                "Greenhouse: fetching %d job details concurrently (max_workers=%d) — %d skipped by title filter",
                len(detail_tasks),
                self.max_workers,
                sum(len(data.get("jobs", [])) for data in board_data.values()) - len(detail_tasks),
            )

            executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
            try:
                future_to_task = {
                    executor.submit(self._fetch_detail, token, item.get("id")): (token, item)
                    for token, item in detail_tasks
                }

                DETAIL_FETCH_TIMEOUT = 60
                try:
                    for fut in concurrent.futures.as_completed(future_to_task, timeout=DETAIL_FETCH_TIMEOUT):
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
                except concurrent.futures.TimeoutError:
                    logger.warning(
                        "Greenhouse detail fetch timed out after %ds, collected %d jobs with details",
                        DETAIL_FETCH_TIMEOUT,
                        len(jobs),
                    )
                finally:
                    for fut in future_to_task:
                        fut.cancel()
            finally:
                executor.shutdown(wait=False)
        else:
            # No detail fetching: build jobs from list endpoint (with title filter)
            for token, data in board_data.items():
                company = token.replace("-", " ").title()

                for item in data.get("jobs", []):
                    title = item.get("title", "")
                    if query_keywords:
                        title_lower = title.lower()
                        if not any(kw in title_lower for kw in query_keywords):
                            continue

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
