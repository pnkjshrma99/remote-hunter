"""Talent.com HTML scraper - remote job listings with salary data."""

import logging
import re
from typing import List

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

TALENT_URL = "https://www.talent.com/jobs"


class TalentScraper(BaseScraper):
    name = "talent"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        query = criteria.query if criteria and criteria.query else "software"
        url = f"{TALENT_URL}?k={query.replace(' ', '+')}&l=remote&remote=1"

        try:
            resp = self.fetch(url)
        except Exception as e:
            logger.warning("Talent.com fetch failed: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        jobs: List[RawJob] = []
        seen: set = set()

        for article in soup.find_all("article"):
            title_el = article.find(
                ["h2", "h3", "a", "span"],
                class_=re.compile(r"title|heading|job", re.I),
            )
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                continue

            text = article.get_text(" ", strip=True)

            # Extract salary
            salary = ""
            sal_match = re.search(r"[\$£€][\d,]+(?:\s*-\s*[\$£€]?[\d,]+)?(?:\s*(?:yearly|month|week|hour|yr|monthly))?", text, re.I)
            if sal_match:
                salary = sal_match.group()

            # Extract company (first segment before common delimiters)
            company = "Unknown"
            for sep in [" • ", " · ", " | ", " - "]:
                parts = text.split(sep, 1)
                if len(parts) > 1:
                    # Company often appears after the first separator
                    candidate = parts[1].strip()
                    # Remove location/salary noise
                    candidate = re.sub(r"[\$£€][\d,].*$", "", candidate).strip()
                    candidate = re.sub(r"•.*$", "", candidate).strip()
                    if candidate and len(candidate) < 100:
                        company = candidate
                        break

            # Location detection
            location = "Remote"
            loc_match = re.search(r"(Remote|Worldwide|Anywhere)", text, re.I)
            if not loc_match:
                # Try to find a city/state pattern
                loc_match = re.search(r"[A-Z][a-z]+(?:,\s*[A-Z]{2})?", text)
                if loc_match:
                    location = loc_match.group()

            posted_at = ""
            date_match = re.search(r"(\d+)\s*(day|hour|minute|week|month|year)\s*ago", text, re.I)
            if date_match:
                posted_at = date_match.group()

            link = ""
            link_el = article.find("a", href=True)
            if link_el:
                href = link_el["href"]
                link = href if href.startswith("http") else f"https://www.talent.com{href}"

            external_id = self.make_external_id(self.name, link or title, title)
            if external_id in seen:
                continue
            seen.add(external_id)

            jobs.append(
                RawJob(
                    external_id=external_id,
                    source=self.name,
                    title=title,
                    company=company,
                    url=link,
                    description=text,
                    location=location,
                    salary=salary,
                    posted_at=posted_at,
                )
            )

        logger.info("Fetched %d jobs from Talent.com", len(jobs))
        return jobs
