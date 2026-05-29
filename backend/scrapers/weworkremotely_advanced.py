"""We Work Remotely extended scraper with search functionality."""

import logging
from typing import List
from urllib.parse import urlencode

from scrapers.base import AuthRequiredError, BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

WEWORKREMOTELY_API = "https://weworkremotely.com/api/v2"


class WeWorkRemotelyAdvancedScraper(BaseScraper):
    name = "weworkremotely_advanced"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """
        FIXED: Scrape We Work Remotely - removed dead category feeds (403)
        Uses the main RSS feed and filters by search query instead.
        """
        jobs: List[RawJob] = []

        try:
            import feedparser

            # FIX: Category-specific feeds are 403 Forbidden
            # Use the main RSS feed and filter client-side instead
            main_feed_url = "https://weworkremotely.com/remote-jobs.rss"
            
            try:
                feed = feedparser.parse(main_feed_url)
                for entry in feed.entries:
                    title = entry.get("title", "")
                    company = entry.get("author", "")
                    job_url = entry.get("link", "")
                    description = entry.get("summary", "") or ""
                    location = "Remote"
                    salary = ""

                    # FIX: Use more permissive matching - check if query appears anywhere
                    if criteria and criteria.query:
                        query_lower = criteria.query.lower()
                        title_lower = title.lower()
                        desc_lower = description.lower()
                        if query_lower not in title_lower and query_lower not in desc_lower:
                            # Check if any query term matches
                            terms = criteria.query.split()
                            if not any(term.lower() in title_lower or term.lower() in desc_lower for term in terms):
                                continue

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
                logger.debug("WWR main feed failed: %s", e)

        except AuthRequiredError:
            logger.warning("WeWorkRemotely Advanced scraper requires authentication")
            return []
        except Exception as e:
            logger.warning("We Work Remotely Advanced scrape failed: %s", e)
            return []

        # Deduplicate
        seen = set()
        unique = []
        for j in jobs:
            if j.external_id not in seen:
                seen.add(j.external_id)
                unique.append(j)
        return unique