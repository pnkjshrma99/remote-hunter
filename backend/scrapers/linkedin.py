"""LinkedIn lightweight adapter with optional cookie-based login.

LinkedIn does not provide a generally available public jobs API, and aggressive
scraping is brittle. This adapter supports two modes:
1. Guest mode (default) - Uses public LinkedIn jobs-guest API (often blocked)
2. Authenticated mode - Uses cookie-based login via LINKEDIN_EMAIL/PASSWORD

When authenticated with valid cookies, the scraper has higher rate limits
and access to more job results.
"""

import logging
import re
from typing import List, Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from app.config import get_settings
from scrapers.base import AuthRequiredError, BaseScraper
from scrapers.auth_session import AuthenticatedScraperMixin, CredentialStore
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)
settings = get_settings()


class LinkedInScraper(AuthenticatedScraperMixin, BaseScraper):
    name = "linkedin"
    auth_source = "linkedin"

    def __init__(self, search_urls: list[str] | None = None):
        super().__init__()
        self.search_urls = search_urls or settings.linkedin_url_list
        self._login_response = None

    def login(self):
        """Authenticate to LinkedIn using credentials from env vars."""
        email, password = self.credentials.get("linkedin")
        client = self.session.get_client()

        # Fetch login page to get CSRF token
        login_page = client.get("https://www.linkedin.com/login")
        soup = BeautifulSoup(login_page.text, "html.parser")
        csrf_input = soup.select_one('input[name="loginCsrfParam"]')
        csrf_token = csrf_input.get("value", "") if csrf_input else ""

        # Submit login form
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
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            },
        )

        if "feed" in str(resp.url) or "checkpoint/challenge" in str(resp.url):
            self._login_response = resp
        else:
            raise AuthRequiredError("LinkedIn login failed - check credentials")

    def fetch_authenticated(self, url: str) -> Optional[object]:
        """Fetch URL using authenticated session if available."""
        if self.session.is_logged_in:
            try:
                client = self.session.get_client()
                resp = client.get(
                    url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        ),
                    },
                )
                if resp.status_code == 200 and "login" not in str(resp.url).lower():
                    return resp
            except Exception as e:
                logger.warning(f"LinkedIn authenticated fetch failed: {e}")
        return None

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
            urls.extend(
                [
                    (
                        "https://www.linkedin.com/jobs-guest/jobs/api/"
                        f"seeMoreJobPostings/search?keywords={keywords}"
                        f"&location=Worldwide{tpr}&f_WT=2&start={start}"
                    )
                    for start in (0, 25, 50)
                ]
            )

        if not urls:
            logger.info("LinkedIn scraper skipped: no query or LINKEDIN_SEARCH_URLS")
            return []

        # Try authenticated mode first
        authed = self.ensure_login()

        jobs: list[RawJob] = []
        for url in urls:
            try:
                if authed:
                    resp = self.fetch_authenticated(url)
                    if resp is None:
                        resp = self.fetch(url)
                else:
                    resp = self.fetch(url)
            except AuthRequiredError:
                logger.warning(
                    "LinkedIn scraper blocked by auth wall. "
                    "Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD env vars for authenticated access."
                )
                return []
            except Exception as exc:
                logger.warning("LinkedIn fetch failed for %s: %s", url, exc)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            cards = soup.select(
                "li, "
                ".base-card, "
                ".job-search-card, "
                ".job-search-card__listitem, "
                ".job-card-container, "
                "[data-job-id], "
                "article.job-card, "
                ".job-card"
            )

            for card in cards:
                title_el = (
                    card.select_one(".base-search-card__title, h3, a, "
                                    ".job-card-list__title, "
                                    ".job-card__title, "
                                    "[data-job-title], "
                                    ".artdeco-entity-lockup__title")
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
                    time_match = re.search(r'(just now|\d+\s*(minute|hour|day|week|month)s?\s*ago)', time_text, re.I)
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
