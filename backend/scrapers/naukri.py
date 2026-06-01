"""Naukri.com scraper - India's largest job portal.

Scrapes remote and international jobs from Naukri.com with advanced filtering.
Note: Naukri's API v2 now returns obfuscated responses, so HTML scraping
is the primary method. API is used as a supplementary source.
"""

import json
import logging
import re
from typing import List, Optional
from urllib.parse import urljoin, quote

from bs4 import BeautifulSoup

from scrapers.base import AuthRequiredError, BaseScraper
from scrapers.auth_session import AuthenticatedScraperMixin
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

NAUKRI_BASE_URL = "https://www.naukri.com"
NAUKRI_API_URL = "https://www.naukri.com/jobapi/v2/search"


class NaukriScraper(AuthenticatedScraperMixin, BaseScraper):
    """Naukri.com job scraper - HTML scraping primary, API fallback."""

    name = "naukri"
    auth_source = "naukri"

    def __init__(self):
        super().__init__()
        self._login_response = None

    def login(self):
        """Login to Naukri.com for authenticated access."""
        email, password = self.credentials.get("naukri")
        client = self.session.get_client()

        # Get login page for CSRF
        login_page = client.get("https://www.naukri.com/nlogin/login")
        soup = BeautifulSoup(login_page.text, "html.parser")

        csrf = soup.select_one('input[name="csrfToken"]')
        csrf_token = csrf.get("value", "") if csrf else ""

        resp = client.post(
            "https://www.naukri.com/nlogin/login",
            data={
                "email": email,
                "password": password,
                "csrfToken": csrf_token,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            },
        )

        if "login" not in str(resp.url).lower():
            self._login_response = resp
        else:
            raise AuthRequiredError("Naukri login failed - check credentials")

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape jobs from Naukri.com."""
        jobs: List[RawJob] = []

        self.ensure_login()

        try:
            # Try HTML scraping first (more reliable)
            html_jobs = self._scrape_html(criteria)
            jobs.extend(html_jobs)

            # Try API as supplement
            if len(jobs) < 20:
                api_jobs = self._scrape_api(criteria)
                jobs.extend(api_jobs)

            # Deduplicate
            seen = set()
            unique_jobs = []
            for job in jobs:
                if job.external_id not in seen:
                    seen.add(job.external_id)
                    unique_jobs.append(job)

            logger.info(f"Naukri: Found {len(unique_jobs)} jobs")
            return unique_jobs

        except AuthRequiredError:
            logger.warning("Naukri scraper requires login - set NAUKRI_EMAIL/PASSWORD")
            return []
        except Exception as e:
            logger.error(f"Naukri scraping failed: {e}")
            return []

    def _scrape_api(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape using Naukri's job API (v2 - may be obfuscated)."""
        jobs: List[RawJob] = []

        try:
            params = self._build_api_params(criteria)
            resp = self.fetch(NAUKRI_API_URL, params=params)
            data = resp.json()

            job_list = data.get("list", data.get("data", []))
            if not job_list:
                logger.debug("Naukri API returned no jobs in 'list' key")
                return []

            for item in job_list:
                try:
                    # API v2 uses obfuscated keys; try to extract what we can
                    title = (item.get("title", "") or
                             item.get("jobtitle", "") or
                             item.get("designation", "") or
                             item.get("CONTDESIG", "") or "")
                    company = (item.get("companyName", "") or
                               item.get("company", "") or "")
                    refno = item.get("REFNO", "") or item.get("jobId", "")
                    city = item.get("CONTCITY", "") or item.get("city", "")

                    if not title or not company:
                        continue

                    url = f"{NAUKRI_BASE_URL}/job-details/{refno}" if refno else ""

                    external_id = self.make_external_id(self.name, refno or url, title)

                    jobs.append(RawJob(
                        external_id=external_id,
                        source=self.name,
                        title=title,
                        company=company,
                        url=url,
                        description="",
                        location=city or "Remote",
                    ))
                except Exception as e:
                    logger.warning(f"Failed to parse Naukri API job: {e}")
                    continue

        except AuthRequiredError:
            raise
        except Exception as e:
            logger.warning(f"Naukri API scraping failed: {e}")

        return jobs

    def _scrape_html(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape using HTML parsing (primary method)."""
        jobs: List[RawJob] = []

        try:
            url = self._build_search_url(criteria)
            resp = self.fetch(url)
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            # Naukri job cards - try several selectors
            job_cards = soup.select('.jobTuple, .jobCard, article[data-job-id], [class*="job-list"] > div')

            for card in job_cards:
                try:
                    title_el = (card.select_one('.title, .jobTitle, h2, a[title]'))
                    title = title_el.get_text(strip=True) if title_el else ""

                    company_el = card.select_one('.company, .subTitle, .companyName, [class*="company"]')
                    company = company_el.get_text(strip=True) if company_el else ""

                    link_el = card.select_one('a[href*="naukri.com"]')
                    job_url = link_el.get('href', '') if link_el else ""
                    if job_url and not job_url.startswith("http"):
                        job_url = urljoin(NAUKRI_BASE_URL, job_url)

                    if not title or not company:
                        continue

                    location_el = card.select_one('.location, .loc, [class*="location"]')
                    location = location_el.get_text(strip=True) if location_el else "Remote"

                    posted_el = card.select_one('.posted, [class*="posted"], .date')
                    posted_at = posted_el.get_text(strip=True) if posted_el else ""

                    external_id = self.make_external_id(self.name, job_url or title, title)

                    jobs.append(RawJob(
                        external_id=external_id,
                        source=self.name,
                        title=title,
                        company=company,
                        url=job_url or "",
                        description="",
                        location=location,
                        posted_at=posted_at,
                    ))
                except Exception as e:
                    logger.warning(f"Failed to parse Naukri HTML job: {e}")
                    continue

        except AuthRequiredError:
            raise
        except Exception as e:
            logger.warning(f"Naukri HTML scraping failed: {e}")

        return jobs

    def _build_api_params(self, criteria: SearchCriteria | None = None) -> dict:
        """Build API parameters from search criteria."""
        params = {
            'urlType': 'search',
            'searchType': 'adv',
            'keyword': criteria.query if criteria else 'remote software engineer',
            'location': 'remote',
            'pageNo': 1,
            'pageSize': 50,
            'sort': 'f',
            'experience': -1,
            'salary': -1,
        }

        if criteria:
            if criteria.remote_only:
                params['location'] = 'remote'
            if criteria.min_experience is not None or criteria.max_experience is not None:
                exp_min = criteria.min_experience or 0
                exp_max = criteria.max_experience or 30
                params['experience'] = f"{exp_min}-{exp_max}"
            if getattr(criteria, 'location', None):
                params['location'] = criteria.location

        return params

    def _build_search_url(self, criteria: SearchCriteria | None = None) -> str:
        """Build search URL for HTML scraping."""
        keyword = criteria.query if criteria else 'remote software engineer'
        keyword = quote(keyword)

        url = f"{NAUKRI_BASE_URL}/{keyword}-jobs"
        if criteria and criteria.remote_only:
            url += "-remote"
        return url
