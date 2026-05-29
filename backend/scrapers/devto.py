"""Dev.to Jobs Scraper

Fetches jobs from Dev.to API - the largest developer community platform.
Dev.to has a robust API that returns classified listings including jobs.
"""

import logging
from typing import List, Optional
from scrapers.base import AuthRequiredError, BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)


class DevToScraper(BaseScraper):
    """Dev.to API scraper for job listings"""

    name = "devto"
    BASE_URL = "https://dev.to/api"

    def _build_search_params(self, criteria: SearchCriteria | None = None) -> dict:
        """Build search parameters for Dev.to API."""
        params = {"category": "jobs"}
        if criteria and criteria.query:
            params["search"] = criteria.query
        return params

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape jobs from Dev.to API."""
        jobs: List[RawJob] = []
        seen_urls: set = set()

        try:
            search_params = self._build_search_params(criteria)
            api_url = f"{self.BASE_URL}/listings"

            try:
                resp = self.fetch(api_url, params=search_params)
                data = resp.json()
            except AuthRequiredError:
                logger.warning("Dev.to API requires authentication")
                return []
            except Exception as e:
                logger.warning(f"Dev.to API fetch failed: {e}")
                return []

            if isinstance(data, list):
                for item in data:
                    title = item.get("title", "")
                    url_value = item.get("url", "") or item.get("slug", "")

                    if url_value in seen_urls:
                        continue
                    seen_urls.add(url_value)

                    user = item.get("user", {}) or {}
                    org = item.get("organization", {}) or {}
                    company = org.get("name", "") or user.get("username", "") or "Dev.to Community"

                    description = item.get("body_markdown", "") or item.get("body_text", "") or item.get("description", "") or ""
                    location = item.get("location", "") or "Remote"

                    tags = item.get("tags", []) or item.get("tag_list", [])
                    if isinstance(tags, list) and any("remote" in t.lower() for t in tags):
                        location = "Remote"

                    if isinstance(tags, list) and not description:
                        description = f"Tags: {', '.join(tags)}"

                    external_id = self.make_external_id(
                        self.name,
                        str(item.get("id", url_value)),
                        title
                    )
                    jobs.append(RawJob(
                        external_id=external_id,
                        source=self.name,
                        title=title,
                        company=company,
                        url=url_value,
                        description=description,
                        location=location,
                        posted_at=str(item.get("created_at", item.get("published_at", ""))),
                    ))

            logger.info(f"Fetched {len(jobs)} jobs from Dev.to")

        except Exception as e:
            logger.error(f"Error fetching Dev.to jobs: {e}")

        return jobs
