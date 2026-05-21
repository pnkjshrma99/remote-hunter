"""No Fluff Jobs scraper - European tech job board."""

import logging
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

NOFLUFFJOBS_API = "https://nofluffjobs.com"


class NoFluffJobsScraper(BaseScraper):
    name = "nofluffjobs"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape No Fluff Jobs board - primarily for European tech roles."""
        jobs: List[RawJob] = []
        search = (criteria.query if criteria else "").strip()

        try:
            import feedparser

            # No Fluff Jobs RSS feed with remote filter
            base_url = "https://nofluffjobs.com/rss?country=ANY&employment=permanent"

            if search:
                base_url += f"&keywords={search.replace(' ', '%20')}"

            try:
                feed = feedparser.parse(base_url)
                for entry in feed.entries:
                    title = entry.get("title", "")
                    company = entry.get("author", "") or "Unknown"
                    job_url = entry.get("link", "")
                    description = entry.get("summary", "") or ""
                    location = "Remote"
                    salary = ""

                    # Extract location from description if available
                    if "location" in description.lower():
                        import re
                        loc_match = re.search(r"Location:\s*([^\n]+)", description)
                        if loc_match:
                            location = loc_match.group(1).strip()

                    external_id = self.make_external_id(self.name, job_url, title)
                    jobs.append(
                        RawJob(
                            external_id=external_id,
                            source=self.name,
                            title=title,
                            company=company,
                            url=job_url,
                            description=description,
                            location=location,
                            salary=salary,
                            posted_at=entry.get("published"),
                        )
                    )
            except Exception as e:
                logger.debug("No Fluff Jobs feed parse failed: %s", e)

        except ImportError:
            logger.warning("feedparser not installed - skipping No Fluff Jobs scraper")
            return []
        except Exception as e:
            logger.warning("No Fluff Jobs scrape failed: %s", e)
            return []

        # Deduplicate
        seen = set()
        unique = []
        for j in jobs:
            if j.external_id not in seen:
                seen.add(j.external_id)
                unique.append(j)
        return unique
