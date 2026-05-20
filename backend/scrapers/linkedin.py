"""LinkedIn lightweight adapter.

LinkedIn does not provide a generally available public jobs API, and aggressive
scraping is brittle. This adapter only runs when the user supplies public search
URLs through LINKEDIN_SEARCH_URLS. It extracts conservative card metadata and
lets the shared filters decide whether a posting is relevant.
"""

import logging
from typing import List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from app.config import get_settings
from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)
settings = get_settings()


class LinkedInScraper(BaseScraper):
    name = "linkedin"

    def __init__(self, search_urls: list[str] | None = None):
        super().__init__()
        self.search_urls = search_urls or settings.linkedin_url_list

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

        jobs: list[RawJob] = []
        for url in urls:
            try:
                response = self.fetch(url)
            except Exception as exc:
                logger.warning("LinkedIn fetch failed for %s: %s", url, exc)
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.select("li, .base-card, .job-search-card, .job-search-card__listitem")
            for card in cards:
                title_el = card.select_one(".base-search-card__title, h3, a")
                company_el = card.select_one(".base-search-card__subtitle, h4")
                location_el = card.select_one(".job-search-card__location, .job-result-card__location")
                link_el = card.select_one("a[href*='/jobs/view/'], a[href*='linkedin.com/jobs']")
                time_el = card.select_one("time")

                title = title_el.get_text(" ", strip=True) if title_el else ""
                company = company_el.get_text(" ", strip=True) if company_el else "LinkedIn"
                link = link_el.get("href", "") if link_el else ""
                location = location_el.get_text(" ", strip=True) if location_el else "Remote"

                if not title or not link:
                    continue

                description = f"{title} {company} {location}"
                posted_at = time_el.get("datetime", "") if time_el else ""
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
