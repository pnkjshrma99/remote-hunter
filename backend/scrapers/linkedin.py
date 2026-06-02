"""LinkedIn job scraper using guest API with Cloudflare bypass.

LinkedIn exposes a public guest API for job listings that requires no login.
However, LinkedIn sits behind Cloudflare which blocks standard httpx requests.
This scraper uses cloudscraper (already in the codebase) to bypass Cloudflare
and extract job listings from LinkedIn's public guest API.

Two modes:
1. Guest mode (default) - Uses cloudscraper to bypass Cloudflare on the
   public jobs-guest API. Cloudscraper solves the JS challenge automatically.
2. Authenticated mode - Uses LINKEDIN_EMAIL/PASSWORD for higher rate limits.
"""

import logging
import re
import time
from typing import List, Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

import httpx
try:
    import cloudscraper
    _cloudscraper = cloudscraper.create_scraper(
        browser=dict(browser="chrome", platform="darwin", mobile=False),
    )
except ImportError:
    _cloudscraper = None

from app.config import get_settings
from scrapers.base import AuthRequiredError, BaseScraper
from scrapers.auth_session import AuthenticatedScraperMixin, CredentialStore
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)
settings = get_settings()


LINKEDIN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


class LinkedInScraper(AuthenticatedScraperMixin, BaseScraper):
    name = "linkedin"
    auth_source = "linkedin"

    def __init__(self, search_urls: list[str] | None = None):
        super().__init__()
        self.search_urls = search_urls or settings.linkedin_url_list
        self._login_response = None

    def login(self):
        email, password = self.credentials.get("linkedin")
        client = self.session.get_client()

        login_page = client.get("https://www.linkedin.com/login")
        soup = BeautifulSoup(login_page.text, "html.parser")
        csrf_input = soup.select_one('input[name="loginCsrfParam"]')
        csrf_token = csrf_input.get("value", "") if csrf_input else ""

        resp = client.post(
            "https://www.linkedin.com/checkpoint/lg/login-submit",
            data={
                "session_key": email,
                "session_password": password,
                "loginCsrfParam": csrf_token,
                "trk": "guest_homepage-basic_sign-in-submit",
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": LINKEDIN_HEADERS["User-Agent"],
            },
        )

        if "feed" in str(resp.url) or "checkpoint/challenge" in str(resp.url):
            self._login_response = resp
        else:
            raise AuthRequiredError("LinkedIn login failed - check credentials")

    def fetch_guest(self, url: str) -> Optional[httpx.Response]:
        """Fetch LinkedIn guest API using cloudscraper to bypass Cloudflare.

        Falls back to regular httpx if cloudscraper is not installed.
        """
        if _cloudscraper is not None:
            try:
                resp = _cloudscraper.get(
                    url,
                    headers=LINKEDIN_HEADERS,
                    timeout=settings.request_timeout_seconds,
                )
                if resp.status_code == 200:
                    content_type = resp.headers.get("content-type", "").lower()
                    if not ("login" in str(resp.url).lower()
                            and "challenge" in str(resp.url).lower()):
                        return httpx.Response(
                            status_code=resp.status_code,
                            text=resp.text,
                            headers=dict(resp.headers),
                        )
                logger.debug("LinkedIn cloudscraper returned %s", resp.status_code)
            except Exception as e:
                logger.warning("LinkedIn cloudscraper fetch failed: %s", e)
        else:
            logger.debug("LinkedIn: cloudscraper not installed, using httpx")

        try:
            with httpx.Client(
                timeout=settings.request_timeout_seconds,
                follow_redirects=True,
                headers=LINKEDIN_HEADERS,
            ) as client:
                resp = client.get(url)
                if resp.status_code == 200 and "login" not in str(resp.url).lower():
                    return resp
        except Exception as e:
            logger.warning("LinkedIn httpx fetch failed: %s", e)

        return None

    def fetch_authenticated(self, url: str) -> Optional[httpx.Response]:
        if self.session.is_logged_in:
            try:
                client = self.session.get_client()
                resp = client.get(url, headers=LINKEDIN_HEADERS)
                if resp.status_code == 200 and "login" not in str(resp.url).lower():
                    return resp
            except Exception as e:
                logger.warning("LinkedIn authenticated fetch failed: %s", e)
        return None

    def _parse_jobs_from_html(self, html: str) -> List[RawJob]:
        """Parse job listings from LinkedIn guest API HTML response."""
        soup = BeautifulSoup(html, "html.parser")
        jobs: list[RawJob] = []

        cards = soup.find_all("li")
        if not cards:
            cards = soup.select(
                ".base-card, .job-search-card, "
                ".job-card-container, [data-job-id], "
                "article.job-card, .job-card"
            )

        for card in cards:
            title_el = (
                card.select_one(".base-search-card__title, h3, a, "
                                ".job-card-list__title, .job-card__title, "
                                "[data-job-title], .artdeco-entity-lockup__title")
            )
            company_el = card.select_one(
                ".base-search-card__subtitle, h4, "
                ".job-card-container__company-name, "
                ".job-card__company-name, "
                ".artdeco-entity-lockup__subtitle"
            )
            location_el = card.select_one(
                ".job-search-card__location, .job-result-card__location, "
                ".job-card-container__metadata-wrapper, "
                ".job-card__location, "
                ".artdeco-entity-lockup__caption"
            )
            link_el = card.select_one(
                "a[href*='/jobs/view/'], "
                "a[href*='linkedin.com/jobs'], "
                "a.job-card-container__link, "
                "a[data-job-id]"
            )
            time_el = card.select_one("time, [datetime], .job-card-container__listed-state")

            title = title_el.get_text(" ", strip=True) if title_el else ""
            company = company_el.get_text(" ", strip=True) if company_el else "LinkedIn"

            link = ""
            if link_el:
                if link_el.name == "a":
                    link = link_el.get("href", "")
                elif link_el.name == "div":
                    inner_link = link_el.select_one("a")
                    if inner_link:
                        link = inner_link.get("href", "")

            location = ""
            if location_el:
                location = location_el.get_text(" ", strip=True)
                location = re.sub(r'^[·\s]+', '', location).strip()
            if not location:
                location = card.get("data-location", "") or card.get("data-search-location", "")
            if not location:
                location = "Remote"

            if not title or not link:
                continue

            description = f"{title} {company} {location}"

            posted_at = ""
            if time_el:
                posted_at = time_el.get("datetime", "") or time_el.get_text(strip=True)
            if not posted_at:
                time_text = card.get_text()
                time_match = re.search(
                    r'(just now|\d+\s*(minute|hour|day|week|month)s?\s*ago)',
                    time_text, re.I,
                )
                if time_match:
                    posted_at = time_match.group(1)

            jobs.append(
                RawJob(
                    external_id=self.make_external_id(self.name, link, title),
                    source=self.name,
                    title=title,
                    company=company,
                    url=link,
                    description=description,
                    location=location,
                    posted_at=posted_at,
                )
            )

        return jobs

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        urls = list(self.search_urls)
        if criteria and criteria.linkedin_urls:
            urls.extend(criteria.linkedin_urls)
        if criteria and criteria.query:
            tpr = ""
            if criteria.posted_within_days:
                seconds = criteria.posted_within_days * 86400
                tpr = f"&f_TPR=r{seconds}"
            keywords = quote_plus(criteria.query)
            for start in (0, 25, 50):
                urls.append(
                    f"https://www.linkedin.com/jobs-guest/jobs/api/"
                    f"seeMoreJobPostings/search?keywords={keywords}"
                    f"&location=Worldwide{tpr}&f_WT=2&start={start}"
                )

        if not urls:
            logger.info("LinkedIn scraper skipped: no query or LINKEDIN_SEARCH_URLS")
            return []

        authed = self.ensure_login()
        all_jobs: list[RawJob] = []

        for url in urls:
            try:
                if authed:
                    resp = self.fetch_authenticated(url)
                else:
                    resp = None

                if resp is None:
                    resp = self.fetch_guest(url)

                if resp is None:
                    logger.debug("LinkedIn: all fetch methods failed for %s", url)
                    continue

            except AuthRequiredError:
                logger.warning(
                    "LinkedIn scraper blocked by auth wall. "
                    "Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD env vars for authenticated access."
                )
                continue
            except Exception as exc:
                logger.warning("LinkedIn fetch failed for %s: %s", url, exc)
                continue

            jobs = self._parse_jobs_from_html(resp.text)
            all_jobs.extend(jobs)

        return all_jobs
