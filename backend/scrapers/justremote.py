"""JustRemote scraper - remote job board."""

import logging
from typing import List
from urllib.parse import quote

from scrapers.base import AuthRequiredError, BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

JUSTREMOTE_API = "https://justremote.co"


class JustRemoteScraper(BaseScraper):
    name = "justremote"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape JustRemote job board - RSS feed."""
        jobs: List[RawJob] = []
        search = (criteria.query if criteria else "").strip()

        try:
            import feedparser

            # FIX: Use proper URL encoding with quote()
            feeds = [
                "https://justremote.co/jobs.rss",
            ]
            
            if search:
                # FIX: Use proper URL encoding instead of manual .replace()
                search_encoded = quote(f"{search} remote")
                feeds.append(f"https://justremote.co/search?q={search_encoded}")
            
            for feed_url in feeds:
                try:
                    feed = feedparser.parse(feed_url)
                    for entry in feed.entries[:50]:
                        title = entry.get("title", "")
                        company = entry.get("author", "")
                        job_url = entry.get("link", "")
                        description = entry.get("summary", "") or ""
                        location = "Remote"
                        salary = ""

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
                    logger.debug("JustRemote feed failed: %s", e)
                    continue

        except AuthRequiredError:
            logger.warning("JustRemote scraper requires authentication")
            return []
        except ImportError:
            logger.warning("feedparser not installed - skipping JustRemote scraper")
            return []
        except Exception as e:
            logger.warning("JustRemote scrape failed: %s", e)
            return []

        # Deduplicate
        seen = set()
        unique = []
        for j in jobs:
            if j.external_id not in seen:
                seen.add(j.external_id)
                unique.append(j)
        return unique