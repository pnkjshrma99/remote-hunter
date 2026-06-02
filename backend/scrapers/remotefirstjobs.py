"""RemoteFirstJobs scraper - remote job board with RSS feeds."""

import logging
import re
from html import unescape
from typing import List

import feedparser

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

RSS_FEED = "https://remotefirstjobs.com/rss/jobs.rss"


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_company(title: str) -> tuple[str, str]:
    parts = title.split(" at ", 1)
    if len(parts) == 2:
        return parts[1].strip(), parts[0].strip()
    return "Unknown", title


class RemoteFirstJobsScraper(BaseScraper):
    name = "remotefirstjobs"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        seen_guids: set = set()

        try:
            resp = self.fetch(RSS_FEED)
            feed = feedparser.parse(resp.content)
        except Exception as e:
            logger.warning("RemoteFirstJobs feed failed: %s", e)
            return []

        for entry in feed.entries:
            guid = entry.get("guid", "")
            if guid in seen_guids:
                continue
            seen_guids.add(guid)

            title = entry.get("title", "")
            link = entry.get("link", "")
            description = _strip_html(
                entry.get("summary", "") or entry.get("description", "")
            )

            company, clean_title = _extract_company(title)

            external_id = self.make_external_id(self.name, link, clean_title)
            jobs.append(
                RawJob(
                    external_id=external_id,
                    source=self.name,
                    title=clean_title,
                    company=company,
                    url=link,
                    description=description,
                    location="Remote",
                    posted_at=entry.get("published", ""),
                )
            )

        logger.info("RemoteFirstJobs: %d unique jobs", len(jobs))
        return jobs
