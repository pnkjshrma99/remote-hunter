"""Y Combinator (Work at a Startup) Jobs Scraper

Fetches jobs from Y Combinator's "Work at a Startup" job board.
YC companies include well-known startups like Stripe, Airbnb, DoorDash, etc.
"""

import logging
import re
from typing import List, Optional
from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)


class YCombinatorScraper(BaseScraper):
    """Y Combinator Work at a Startup job scraper"""

    name = "ycombinator"
    BASE_URL = "https://www.ycombinator.com"
    JOBS_API = "https://www.ycombinator.com/jobs"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """
        Scrape jobs from Y Combinator's job board.
        Uses their career API endpoint.
        """
        jobs: List[RawJob] = []

        try:
            # YC uses a search API for their jobs
            api_url = f"{self.BASE_URL}/assets/api/jobs/search"

            search_query = "remote"
            if criteria and criteria.query:
                search_query = f"{search_query} {criteria.query}"

            params = {
                "query": search_query,
                "limit": 50,
                "remote": "true",
                "sort_by": "newest",
            }

            resp = self.fetch(api_url, params=params)
            data = resp.json()

            jobs_list = data.get("jobs", [])
            if isinstance(jobs_list, list):
                for item in jobs_list:
                    job = self._parse_job(item)
                    if job:
                        jobs.append(job)

            logger.info(f"Fetched {len(jobs)} jobs from Y Combinator")

            # If API approach fails, fall back to HTML scraping
            if not jobs:
                jobs = self._scrape_html(criteria)

        except Exception as e:
            logger.warning(f"YC API approach failed, trying HTML fallback: {e}")
            try:
                jobs = self._scrape_html(criteria)
            except Exception as e2:
                logger.error(f"Error fetching Y Combinator jobs: {e2}")

        return jobs

    def _scrape_html(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Fallback: scrape jobs from HTML page"""
        jobs: List[RawJob] = []

        params = {"remote": "true"}
        if criteria and criteria.query:
            params["query"] = criteria.query

        resp = self.fetch(self.JOBS_API, params=params)
        html = resp.text

        # Parse job listing cards from HTML
        # YC jobs are in structured divs with data-* attributes
        job_pattern = re.compile(
            r'<div[^>]*class="[^"]*job[^"]*"[^>]*>.*?'
            r'<a[^>]*href="(/jobs/[^"]+)"[^>]*>.*?'
            r'<h3[^>]*>(.*?)</h3>.*?'
            r'<span[^>]*class="[^"]*company[^"]*"[^>]*>(.*?)</span>',
            re.DOTALL | re.IGNORECASE,
        )

        for match in job_pattern.finditer(html):
            try:
                job_path = match.group(1).strip()
                title = match.group(2).strip()
                company = match.group(3).strip()

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

    def _parse_job(self, job_data: dict) -> Optional[RawJob]:
        """Parse job data from API response"""
        try:
            title = job_data.get("title", "") or job_data.get("job_title", "")
            company = ""
            company_data = job_data.get("company", {})
            if isinstance(company_data, dict):
                company = company_data.get("name", "") or company_data.get("company_name", "")
            elif isinstance(company_data, str):
                company = company_data

            slug = job_data.get("slug", "") or job_data.get("id", "")
            job_url = f"{self.BASE_URL}/jobs/{slug}" if slug else ""

            description = job_data.get("description", "") or job_data.get("job_description", "")
            location = job_data.get("location", "") or job_data.get("job_location", "")
            if not location or "remote" in location.lower():
                location = "Remote"

            # YC often returns salary as object or string
            salary = ""
            salary_data = job_data.get("salary", {}) or job_data.get("compensation", {})
            if isinstance(salary_data, dict):
                min_sal = salary_data.get("min", salary_data.get("minCompensation"))
                max_sal = salary_data.get("max", salary_data.get("maxCompensation"))
                currency = salary_data.get("currency", "USD")
                if min_sal and max_sal:
                    salary = f"{currency} {min_sal:,} - {max_sal:,}"
                elif min_sal:
                    salary = f"{currency} {min_sal:,}+"
            elif isinstance(salary_data, str):
                salary = salary_data

            external_id = self.make_external_id(
                self.name,
                str(job_data.get("id", job_data.get("job_id", slug))),
                title,
            )

            return RawJob(
                external_id=external_id,
                source=self.name,
                title=title,
                company=company,
                url=job_url,
                description=description,
                location=location,
                salary=salary,
                posted_at=job_data.get("created_at", job_data.get("posted_at", "")),
            )
        except Exception as e:
            logger.error(f"Error parsing Y Combinator job: {e}")
            return None