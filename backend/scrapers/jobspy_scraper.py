"""Multi-site job scraper using JobSpy library.

Scrapes LinkedIn, Indeed, Glassdoor, Google Jobs, and ZipRecruiter
concurrently via Playwright automation. Gracefully degrades if
Playwright is not installed (returns empty results).
"""

import logging
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

JOBSPY_SITES = ["linkedin", "indeed", "glassdoor", "google", "zip_recruiter"]

try:
    import pandas as pd
    from jobspy import scrape_jobs as _jobspy_scrape

    _jobspy_available = True
except ImportError:
    _jobspy_available = False
    logger.warning("python-jobspy not installed — JobSpyScraper disabled")


class JobSpyScraper(BaseScraper):
    """Multi-site scraper using JobSpy (Playwright-based).

    Covers LinkedIn, Indeed, Glassdoor, Google Jobs, and ZipRecruiter.
    Requires `playwright install chromium` to be run once.
    """

    name = "jobspy"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        if not _jobspy_available:
            logger.warning("JobSpyScraper: python-jobspy not available")
            return []

        query = (criteria and criteria.query) or "DevOps Engineer"
        hours_old = (criteria and criteria.posted_within_days * 24) or 336

        try:
            df: pd.DataFrame = _jobspy_scrape(
                site_name=JOBSPY_SITES,
                search_term=query,
                location="remote",
                results_wanted=50,
                hours_old=hours_old,
                linkedin_fetch_description=True,
            )
        except Exception as e:
            logger.error("JobSpyScraper: scrape failed — %s", e)
            return []

        if df is None or df.empty:
            logger.info("JobSpyScraper: no jobs returned")
            return []

        logger.info("JobSpyScraper: %d raw jobs from %s", len(df), JOBSPY_SITES)
        jobs: List[RawJob] = []
        for _, row in df.iterrows():
            try:
                job_id = str(row.get("id", ""))
                title = str(row.get("title", "") or "")
                company = str(row.get("company", "") or "")
                url = str(row.get("job_url", "") or "")
                description = str(row.get("description", "") or "")
                location = str(row.get("location", "") or "Remote")
                posted_at = str(row.get("date_posted", "") or "")

                if not title or not company:
                    continue

                ext_id = self.make_external_id(self.name, job_id or url, title)
                jobs.append(
                    RawJob(
                        external_id=ext_id,
                        source=self.name,
                        title=title,
                        company=company,
                        url=url,
                        description=description,
                        location=location,
                        posted_at=posted_at,
                    )
                )
            except Exception as e:
                logger.debug("JobSpyScraper: skipped row — %s", e)

        logger.info("JobSpyScraper: %d valid jobs", len(jobs))
        return jobs
