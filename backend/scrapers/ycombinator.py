"""Y Combinator (Work at a Startup) Jobs Scraper

Fetches jobs from Y Combinator's "Work at a Startup" job board.
YC companies include well-known startups like Stripe, Airbnb, DoorDash, etc.

Note: YC jobs now require authentication to view details. The public job
listings page at ycombinator.com/jobs shows job cards but redirects to
account.ycombinator.com for applications. This scraper parses the public
HTML for basic job info.
"""

import logging
import re
from typing import List, Optional
from scrapers.base import AuthRequiredError, BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)


class YCombinatorScraper(BaseScraper):
    """Y Combinator Work at a Startup job scraper"""

    name = "ycombinator"
    BASE_URL = "https://www.ycombinator.com"
    JOBS_URL = "https://www.ycombinator.com/jobs"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape public job listings from Y Combinator job board."""
        try:
            return self._scrape_html(criteria)
        except AuthRequiredError:
            logger.warning("Y Combinator scraper requires authentication")
            return []
        except Exception as e:
            logger.error(f"Error fetching Y Combinator jobs: {e}")
            return []

    def _scrape_html(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape jobs from public HTML page."""
        jobs: List[RawJob] = []

        params = {"remote": "true"}
        if criteria and criteria.query:
            params["q"] = criteria.query

        resp = self.fetch(self.JOBS_URL, params=params)
        html = resp.text

        # Match job cards - YC uses divs with job listing data
        # Pattern: <a href="/jobs/..."> ... <div class="...">Title</div> ... <div class="...">Company</div>
        job_pattern = re.compile(
            r'<a[^>]*href="(/jobs/[^"]+)"[^>]*>.*?'
            r'<div[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</div>.*?'
            r'<div[^>]*class="[^"]*company[^"]*"[^>]*>(.*?)</div>',
            re.DOTALL | re.IGNORECASE,
        )

        for match in job_pattern.finditer(html):
            try:
                job_path = match.group(1).strip()
                title = match.group(2).strip()
                company = match.group(3).strip()

                if not title or not company:
                    continue

                external_id = self.make_external_id(
                    self.name, job_path, title
                )

                jobs.append(RawJob(
                    external_id=external_id,
                    source=self.name,
                    title=title,
                    company=company,
                    url=f"{self.BASE_URL}{job_path}",
                    description="",
                    location="Remote",
                    posted_at="",
                ))
            except Exception:
                continue

        logger.info(f"Fetched {len(jobs)} jobs from Y Combinator HTML")
        return jobs
