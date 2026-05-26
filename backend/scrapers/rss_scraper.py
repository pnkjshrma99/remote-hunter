"""Generic RSS feed scraper for job boards."""

import logging
import re
from html import unescape
from typing import List
from xml.etree import ElementTree as ET

import feedparser

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class RSSScraper(BaseScraper):
    """Configurable RSS scraper."""

    def __init__(self, name: str, feed_url: str, default_location: str = "Remote"):
        super().__init__()
        self.name = name
        self.feed_url = feed_url
        self.default_location = default_location

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        try:
            resp = self.fetch(self.feed_url)
            feed = feedparser.parse(resp.content)
        except Exception as e:
            logger.warning("RSS %s failed: %s", self.name, e)
            return []

        for entry in feed.entries:
            title = entry.get("title", "")
            link = entry.get("link", "")
            description = _strip_html(
                entry.get("summary", "") or entry.get("description", "")
            )
            company = ""
            if hasattr(entry, "author"):
                company = entry.author
            # Try to extract company from title "Company: Role"
            if ":" in title and not company:
                parts = title.split(":", 1)
                if len(parts) == 2:
                    company, title = parts[0].strip(), parts[1].strip()

            external_id = self.make_external_id(self.name, link, title)
            jobs.append(
                RawJob(
                    external_id=external_id,
                    source=self.name,
                    title=title,
                    company=company or "Unknown",
                    url=link,
                    description=description,
                    location=self.default_location,
                    posted_at=entry.get("published", ""),
                )
            )
        return jobs


class WeWorkRemotelyScraper(RSSScraper):
    name = "weworkremotely"

    def __init__(self):
        super().__init__(
            name="weworkremotely",
            feed_url="https://weworkremotely.com/remote-jobs.rss",
            default_location="Remote",
        )


class WorkingNomadsScraper(RSSScraper):
    name = "workingnomads"

    def __init__(self):
        super().__init__(
            name="workingnomads",
            feed_url="https://www.workingnomads.com/jobsfeed/remote-devops-jobs.rss",
            default_location="Remote Worldwide",
        )


class HimalayasScraper(RSSScraper):
    name = "himalayas"

    def __init__(self):
        super().__init__(
            name="himalayas",
            feed_url="https://himalayas.app/jobs/rss",
            default_location="Remote",
        )


class JobicyScraper(RSSScraper):
    name = "jobicy"

    def __init__(self):
        super().__init__(
            name="jobicy",
            feed_url="https://jobicy.com/remote-jobs/feed",
            default_location="Remote",
        )


class JobspressoScraper(RSSScraper):
    name = "jobspresso"

    def __init__(self):
        super().__init__(
            name="jobspresso",
            feed_url="https://jobspresso.co/remote-jobs/feed/",
            default_location="Remote",
        )
