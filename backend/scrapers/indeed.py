"""Indeed job scraper.

Fetches job listings from Indeed search results.
Uses HTML parsing since Indeed has deprecated their public API.
"""

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
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


class IndeedScraper(BaseScraper):
    """Scrapes job listings from Indeed search results."""

    name = "indeed"
    friendly_name = "Indeed"

    BASE_URLS = ["https://www.indeed.com", "https://www.indeed.co.uk"]
    MAX_PAGES = 5

    def get_source_params(self, criteria) -> dict:
        params = {}
        if criteria.query:
            params["q"] = criteria.query
        if criteria.remote_only:
            params["remote"] = "yes"
        if criteria.posted_within_days:
            if criteria.posted_within_days <= 1:
                params["fromage"] = "1"
            elif criteria.posted_within_days <= 3:
                params["fromage"] = "3"
            elif criteria.posted_within_days <= 7:
                params["fromage"] = "7"
            elif criteria.posted_within_days <= 14:
                params["fromage"] = "14"
            elif criteria.posted_within_days <= 30:
                params["fromage"] = "30"
        params["sort"] = "date"
        params["limit"] = "50"
        return params

    def scrape(self, criteria) -> List[RawJob]:
        params = self.get_source_params(criteria)
        query = params.get("q", "software engineer")
        remote = params.get("remote", "yes")
        fromage = params.get("fromage", "14")
        limit = params.get("limit", "50")

        all_jobs: List[RawJob] = []
        seen_keys: set = set()

        # Try multiple Indeed domains
        for base_url in self.BASE_URLS:
            for page in range(self.MAX_PAGES):
                start = page * int(limit)
                url = (f"{base_url}/jobs?q={quote_plus(query)}"
                       f"&remote={remote}&fromage={fromage}"
                       f"&sort=date&start={start}&limit={limit}")

                try:
                    jobs = self._fetch_page(url, base_url)
                    if not jobs:
                        continue

                    for job in jobs:
                        key = job.external_id
                        if key not in seen_keys:
                            seen_keys.add(key)
                            all_jobs.append(job)

                    logger.info(f"Indeed {base_url} page {page + 1}: {len(jobs)} jobs")

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 403:
                        logger.debug(f"Indeed blocked on {base_url}")
                        break
                except Exception as e:
                    logger.debug(f"Indeed page {page + 1} failed: {e}")
                    break

        logger.info(f"Indeed total: {len(all_jobs)} unique jobs")
        return all_jobs

    def _fetch_page(self, url: str, base_url: str) -> List[RawJob]:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Referer": f"{base_url}/",
        }

        with httpx.Client(follow_redirects=True, timeout=15) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            jobs: List[RawJob] = []

            # Try multiple selectors for Indeed's varying layouts
            card_selectors = [
                {"class": re.compile(r"job_seen_beacon|cardOutline|custom_card|job_card|card")},
                {"data-testid": re.compile(r"job|slider")},
                {"itemtype": "http://schema.org/JobPosting"},
            ]

            for selector_kwargs in card_selectors:
                cards = soup.find_all("div", **selector_kwargs)
                for card in cards:
                    try:
                        job = self._parse_card(card, base_url)
                        if job:
                            jobs.append(job)
                    except Exception:
                        pass
                if jobs:
                    break

            if not jobs:
                # Fallback: look for any linked job title
                for link in soup.find_all("a", href=re.compile(r"/company/|/pagead/|/rc/|/jobs/view")):
                    try:
                        title_el = link.find("span") or link
                        title = title_el.get_text(strip=True)
                        if title and len(title) > 5 and not any(
                            x in title.lower() for x in ["apply", "sign in", "create"]
                        ):
                            href = link.get("href", "")
                            if href.startswith("/"):
                                href = f"{base_url}{href}"
                            ext_id = self.make_external_id(self.name, href, title)
                            if ext_id not in {j.external_id for j in jobs}:
                                jobs.append(RawJob(
                                    external_id=ext_id,
                                    source=self.name,
                                    title=title,
                                    company="Unknown",
                                    url=href,
                                    location="Remote",
                                    posted_at=datetime.utcnow().isoformat(),
                                ))
                    except Exception:
                        pass

            return jobs

    def _parse_card(self, card, base_url: str) -> Optional[RawJob]:
        title_el = (
            card.find("h2", class_=re.compile(r"jobTitle|title"))
            or card.find("a", class_=re.compile(r"jcs-JobTitle|title"))
            or card.find("span", class_=re.compile(r"title"))
            or card.find("a", {"data-testid": re.compile(r"job-title")})
        )
        company_el = (
            card.find("span", class_=re.compile(r"companyName|company"))
            or card.find("div", class_=re.compile(r"company"))
            or card.find("a", {"data-testid": re.compile(r"company")})
        )
        location_el = (
            card.find("div", class_=re.compile(r"companyLocation|location"))
            or card.find("span", class_=re.compile(r"location"))
            or card.find("div", {"data-testid": re.compile(r"location")})
        )
        url_el = (
            card.find("a", class_=re.compile(r"jcs-JobTitle|title"))
            or card.find("a", href=re.compile(r"/company/|/pagead/|/rc/|/jobs/view"))
        )

        if not title_el:
            return None

        title = title_el.get_text(strip=True)
        if not title or len(title) < 3:
            return None

        company = company_el.get_text(strip=True) if company_el else "Unknown"
        location = location_el.get_text(strip=True) if location_el else "Remote"

        # Clean location
        location = re.sub(r"\s+", " ", location).strip()

        job_url = None
        if url_el and url_el.get("href"):
            href = url_el["href"]
            if href.startswith("/"):
                job_url = f"{base_url}{href}"
            elif href.startswith("http"):
                job_url = href

        if not job_url:
            return None

        external_id = self.make_external_id(self.name, job_url, title)

        return RawJob(
            external_id=external_id,
            source=self.name,
            title=title,
            company=company,
            url=job_url,
            description="",
            location=location,
            posted_at=datetime.utcnow().isoformat(),
        )
