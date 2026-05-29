"""AngelList/Wellfound jobs scraper.

Wellfound (formerly AngelList) has a public jobs page at
https://wellfound.com/jobs that can be scraped without auth.

This scraper delegates to the Wellfound scraper since both
names refer to the same platform.
"""

import logging
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria
from scrapers.wellfound import WellfoundScraper

logger = logging.getLogger(__name__)


class AngelListScraper(BaseScraper):
    name = "angellist"

    def __init__(self):
        super().__init__()
        self._delegate = WellfoundScraper()

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Delegate to Wellfound scraper (same platform)."""
        jobs = self._delegate.scrape(criteria)
        for job in jobs:
            job.source = self.name
            job.external_id = self.make_external_id(self.name, job.url, job.title)
        logger.info(f"AngelList (via Wellfound): {len(jobs)} jobs")
        return jobs
