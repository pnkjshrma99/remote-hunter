"""Google Jobs scraper.

Fetches job listings from Google's job search results page.
Google Jobs aggregates from many sources (LinkedIn, Indeed, Glassdoor, etc.),
making this a high-value single endpoint.
"""

import json
import logging
import random
import re
from datetime import datetime
from typing import Optional, List
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.filters import RawJob

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


class GoogleJobsScraper(BaseScraper):
    """Scrapes job listings from Google Jobs search results."""

    name = "google_jobs"
    friendly_name = "Google Jobs"

    def get_source_params(self, criteria) -> dict:
        return {}

    def scrape(self, criteria) -> List[RawJob]:
        query = criteria.query or "software engineer"
        url = f"https://www.google.com/search?q={quote_plus(query + ' remote job')}&ibp=htl;jobs"

        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        try:
            with httpx.Client(follow_redirects=True, timeout=15) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                html = response.text

                jobs = self._parse_jobs_from_html(html, query)
                logger.info(f"Google Jobs: {len(jobs)} jobs")
                return jobs

        except Exception as e:
            logger.warning(f"Google Jobs scrape failed: {e}")
            return []

    def _parse_jobs_from_html(self, html: str, query: str) -> List[RawJob]:
        jobs: List[RawJob] = []
        seen: set = set()

        soup = BeautifulSoup(html, "html.parser")

        # Strategy 1: Look for JSON-LD structured data
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "ItemList":
                    for item in data.get("itemListElement", []):
                        job_data = item.get("item", {})
                        job = self._parse_ld_job(job_data, query)
                        if job and job.external_id not in seen:
                            seen.add(job.external_id)
                            jobs.append(job)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "JobPosting":
                            job = self._parse_ld_job(item, query)
                            if job and job.external_id not in seen:
                                seen.add(job.external_id)
                                jobs.append(job)
            except (json.JSONDecodeError, AttributeError):
                pass

        # Strategy 2: Parse Google's job card HTML structure
        if not jobs:
            for card in soup.select("[class*='job'] [class*='title'], [jsname] a"):
                try:
                    title_el = card
                    title = title_el.get_text(strip=True)
                    if not title or len(title) < 5:
                        continue

                    href = title_el.get("href", "")
                    if not href:
                        continue

                    ext_id = self.make_external_id(self.name, href, title)

                    if ext_id not in seen:
                        seen.add(ext_id)
                        jobs.append(RawJob(
                            external_id=ext_id,
                            source=self.name,
                            title=title,
                            company="Unknown",
                            url=f"https://www.google.com{href}" if href.startswith("/") else href,
                            description="",
                            location="Remote",
                            posted_at=datetime.utcnow().isoformat(),
                        ))
                except Exception:
                    pass

        return jobs

    def _parse_ld_job(self, data: dict, query: str) -> Optional[RawJob]:
        try:
            title = data.get("title", "")
            company = data.get("hiringOrganization", {}).get("name", "Unknown")
            url = data.get("url", "")
            location = data.get("jobLocation", {})
            location_name = ""
            if isinstance(location, dict):
                address = location.get("address", {})
                if isinstance(address, dict):
                    location_name = address.get("addressLocality", "") or address.get("addressRegion", "") or ""
            elif isinstance(location, list) and location:
                addr = location[0].get("address", {})
                location_name = addr.get("addressLocality", "") or ""

            description = data.get("description", "") or ""

            if not title or not url:
                return None

            import hashlib
            ext_id = f"googlejobs-{hashlib.md5(url.encode()).hexdigest()[:12]}"

            # Extract posted date
            posted = data.get("datePosted", "")

            return RawJob(
                external_id=ext_id,
                source=self.name,
                title=title.strip(),
                company=company.strip(),
                url=url,
                description=description[:2000],
                location=location_name or "Remote",
                posted_at=posted or datetime.utcnow().isoformat(),
            )
        except Exception as e:
            logger.debug(f"Google Jobs LD parse error: {e}")
            return None
