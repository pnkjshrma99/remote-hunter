"""Stack Overflow Jobs scraper - retired.

Note: Stack Overflow Jobs shut down in 2022. The old RSS feed at
https://stackoverflow.com/jobs/feed returns 404 and the API endpoint
at api.stackexchange.com/2.3/jobs no longer returns job listings.

This scraper is kept for backward compatibility but will always
return empty results with a clear log message.
"""

import logging
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)


class StackOverflowScraper(BaseScraper):
    name = "stackoverflow"
    enabled = True

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Return empty - StackOverflow Jobs shut down in 2022.

        The old API endpoint (api.stackexchange.com/2.3/jobs) no longer
        returns job listings. Consider using the 'devto' or 'github_jobs'
        scrapers for developer-focused tech listings.
        """
        logger.info(
            "StackOverflow Jobs shut down in 2022. "
            "Use 'devto' or 'github_jobs' scrapers for tech job listings instead."
        )
        return []
