"""HN "Who's Hiring" scraper using Algolia API.

Replaces the fragile YCombinator HTML scraper with a reliable
JSON API from Algolia (the same search backend that powers HN).
No authentication required.
"""

import logging
import re
from datetime import datetime, timezone
from typing import List

import httpx

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

ALGOLIA_API = "https://hn.algolia.com/api/v1/search"
USER_AGENT = "Mozilla/5.0 (compatible; RemoteHunter/1.0)"


def _fetch_algolia(params: dict) -> dict | None:
    headers = {"User-Agent": USER_AGENT}
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(ALGOLIA_API, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("HN Algolia API error: %s", e)
        return None


REMOTE_KEYWORDS = [
    "remote", "anywhere", "worldwide", "global", "distributed",
    "work from home", "wfh", "home office", "virtual",
]


def _is_remote_job(text: str) -> bool:
    return any(kw in text.lower() for kw in REMOTE_KEYWORDS)


def _parse_comment_listing(body: str, story_title: str) -> List[dict]:
    """Parse an HN comment for job listings.

    Each line starting with '|' or a company name followed by '|'
    is treated as a listing like 'Company | Title | Location | ...'
    """
    jobs: List[dict] = []
    lines = body.split("\n")
    for line in lines:
        line = line.strip()
        if not line or line.startswith(">"):
            continue
        parts = [p.strip() for p in re.split(r"\s*\|\s*", line)]
        if len(parts) >= 2:
            company = parts[0]
            title = parts[1]
            location = parts[2] if len(parts) > 2 else ""
            if company and title and (_is_remote_job(location) or _is_remote_job(title)):
                jobs.append({
                    "company": company,
                    "title": title,
                    "location": location,
                })
    return jobs


class HNAlgoliaScraper(BaseScraper):
    """HN 'Who's Hiring' scraper via Algolia API.

    Fetches the latest 'Who is hiring?' threads and extracts
    job listings from their comments. Reliable JSON API, no auth.
    """

    name = "hn_algolia"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        params = {
            "tags": "story,author_whoishiring",
            "hitsPerPage": 10,
            "numericFilters": "points>5",
        }
        data = _fetch_algolia(params)
        if not data or "hits" not in data:
            return []

        threads = data.get("hits", [])
        if not threads:
            logger.info("HN Algolia: no hiring threads found")
            return []

        logger.info("HN Algolia: found %d hiring threads", len(threads))
        jobs: List[RawJob] = []
        seen_titles: set = set()

        for thread in threads:
            story_title = thread.get("title", "")
            object_id = thread.get("objectID", "")

            if "who is hiring" not in story_title.lower():
                continue

            # Fetch the thread's children (comments)
            children_params = {
                "tags": f"comment,parent_{object_id}",
                "hitsPerPage": 200,
            }
            comments_data = _fetch_algolia(children_params)
            if not comments_data:
                continue

            for hit in comments_data.get("hits", []):
                body = hit.get("comment_text", "") or ""
                if len(body) < 20:
                    continue

                listings = _parse_comment_listing(body, story_title)
                for listing in listings:
                    title = listing["title"]
                    company = listing["company"]
                    # Dedup by title+company
                    key = f"{title}|{company}".lower()
                    if key in seen_titles:
                        continue
                    seen_titles.add(key)

                    posted_at = thread.get("created_at", "")
                    ext_id = self.make_external_id(self.name, key, title)
                    jobs.append(
                        RawJob(
                            external_id=ext_id,
                            source=self.name,
                            title=title,
                            company=company,
                            url=f"https://news.ycombinator.com/item?id={object_id}",
                            description=f"Hiring thread: {story_title}",
                            location=listing.get("location", "Remote"),
                            posted_at=posted_at,
                        )
                    )

        logger.info("HN Algolia: %d remote jobs parsed", len(jobs))
        return jobs
