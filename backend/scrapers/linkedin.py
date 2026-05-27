"""LinkedIn lightweight adapter.

LinkedIn does not provide a generally available public jobs API, and aggressive
scraping is brittle. This adapter only runs when the user supplies public search
URLs through LINKEDIN_SEARCH_URLS. It extracts conservative card metadata and
lets the shared filters decide whether a posting is relevant.
"""

import logging
import re
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
            
            # FIX: Updated selectors for current LinkedIn HTML structure (2024-2025)
            # LinkedIn's jobs API page uses different class names now
            # Try multiple selector patterns to be resilient to HTML changes
            cards = soup.select(
                "li, "
                ".base-card, "
                ".job-search-card, "
                ".job-search-card__listitem, "
                ".job-card-container, "  # New LinkedIn class
                "[data-job-id], "  # New attribute-based selector
                "article.job-card, "  # Another pattern
                ".job-card"  # Generic fallback
            )
            
            for card in cards:
                # Try multiple selector patterns for each field
                title_el = (
                    card.select_one(".base-search-card__title, h3, a, "
                                    ".job-card-list__title, "  # New LinkedIn class
                                    ".job-card__title, "  # Another new class
                                    "[data-job-title], "  # Attribute selector
                                    ".artdeco-entity-lockup__title")
                )
                company_el = card.select_one(
                    ".base-search-card__subtitle, h4, "
                    ".job-card-container__company-name, "  # New class
                    ".job-card__company-name, "  # Another new class
                    ".artdeco-entity-lockup__subtitle"
                )
                location_el = card.select_one(
                    ".job-search-card__location, .job-result-card__location, "
                    ".job-card-container__metadata-wrapper, "  # New class
                    ".job-card__location, "  # Another new class
                    ".artdeco-entity-lockup__caption"
                )
                link_el = card.select_one(
                    "a[href*='/jobs/view/'], "
                    "a[href*='linkedin.com/jobs'], "
                    "a.job-card-container__link, "  # New class
                    "a[data-job-id]"  # Attribute selector
                )
                time_el = card.select_one("time, [datetime], .job-card-container__listed-state")

                title = title_el.get_text(" ", strip=True) if title_el else ""
                company = company_el.get_text(" ", strip=True) if company_el else "LinkedIn"
                
                # FIX: Better link extraction
                link = ""
                if link_el:
                    if link_el.name == "a":
                        link = link_el.get("href", "")
                    elif link_el.name == "div":
                        inner_link = link_el.select_one("a")
                        if inner_link:
                            link = inner_link.get("href", "")
                
                # FIX: Better location extraction
                location = ""
                if location_el:
                    location = location_el.get_text(" ", strip=True)
                    # Remove "·" separator and "Remote" prefix if present
                    location = re.sub(r'^[·\s]+', '', location).strip()
                
                if not location:
                    # Try to extract location from the job card's data attributes
                    location = card.get("data-location", "") or card.get("data-search-location", "")
                
                if not location:
                    location = "Remote"

                if not title or not link:
                    continue

                # FIX: Extract description from data attributes or build from available info
                description = f"{title} {company} {location}"
                
                # Try to get posted date from text content
                posted_at = ""
                if time_el:
                    posted_at = time_el.get("datetime", "") or time_el.get_text(strip=True)
                if not posted_at:
                    # Try to find time text in the card
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