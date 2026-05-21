"""We Work Remotely extended scraper with search functionality."""

import logging
from typing import List
from urllib.parse import urlencode

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

WEWORKREMOTELY_API = "https://weworkremotely.com/api/v2"


class WeWorkRemotelyAdvancedScraper(BaseScraper):
    name = "weworkremotely_advanced"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """
        Scrape We Work Remotely with search capability.
        Note: This uses RSS as the main API requires authentication.
        """
        jobs: List[RawJob] = []

        try:
            # We Work Remotely RSS feeds for different categories
            feeds = {
                "devops": "https://weworkremotely.com/categories/devops-sysadmin/feed",
                "backend": "https://weworkremotely.com/categories/back-end/feed",
                "frontend": "https://weworkremotely.com/categories/front-end/feed",
                "full-stack": "https://weworkremotely.com/categories/full-stack/feed",
                "marketing": "https://weworkremotely.com/categories/marketing/feed",
            }

            import feedparser

            for category, feed_url in feeds.items():
                try:
                    feed = feedparser.parse(feed_url)
                    for entry in feed.entries[:50]:
                        title = entry.get("title", "")
                        company = entry.get("author", "")
                        job_url = entry.get("link", "")
                        description = entry.get("summary", "") or ""
                        location = "Remote"
                        salary = ""

                        if criteria and criteria.query.lower() not in title.lower():
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
                    logger.debug("WWR feed %s failed: %s", category, e)
                    continue

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
