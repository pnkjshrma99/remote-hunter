"""AngelList (Wellfound) jobs scraper for startup positions."""

import logging
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

ANGELLIST_API = "https://api.wellfound.com/graphql"


class AngelListScraper(BaseScraper):
    name = "angellist"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape AngelList (Wellfound) jobs - requires authentication."""
        # AngelList/Wellfound now requires API authentication
        # The RSS endpoint redirects to wellfound.com which is blocked
        logger.warning("AngelList scraper requires API authentication. Skipping.")
        return []
