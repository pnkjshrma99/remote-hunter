"""RemoteYeah scraper - remote job board with RSS feed."""

import logging
import re
from html import unescape
from typing import List

import feedparser

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

RSS_FEED = "https://remoteyeah.com/rss.xml"


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


_BOARD_SUFFIXES = [
    " LinkedIn Board", " LinkedIn", " Board", " Careers",
]


def _extract_company(title: str) -> tuple[str, str]:
    parts = title.split(" at ", 1)
    if len(parts) == 2:
        company = parts[1].strip()
        for suffix in _BOARD_SUFFIXES:
            if company.endswith(suffix):
                company = company[: -len(suffix)]
                break
        clean_title = parts[0].strip()
        return company, clean_title
    return "Unknown", title


class RemoteYeahScraper(BaseScraper):
    name = "remoteyeah"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        seen_links: set = set()

        try:
            resp = self.fetch(RSS_FEED)
            feed = feedparser.parse(resp.content)
        except Exception as e:
            logger.warning("RemoteYeah feed failed: %s", e)
            return []

        for entry in feed.entries:
            link = entry.get("link", "")
            if link in seen_links:
                continue
            seen_links.add(link)

            title = entry.get("title", "")
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

        logger.info("RemoteYeah: %d unique jobs", len(jobs))
        return jobs
