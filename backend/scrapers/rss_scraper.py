"""Generic RSS feed scraper for job boards."""

import logging
import re
from html import unescape
from typing import List, Optional
from xml.etree import ElementTree as ET

import feedparser

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

JOB_TITLE_KEYWORDS = [
    "engineer", "developer", "manager", "designer", "analyst", "architect",
    "scientist", "specialist", "coordinator", "administrator", "director",
    "lead", "head", "chief", "officer", "consultant", "associate", "intern",
    "trainee", "support", "sales", "marketing", "product", "qa", "test",
    "devops", "sre", "platform", "infrastructure", "back-end", "backend",
    "front-end", "frontend", "full-stack", "fullstack", "data", "mobile",
    "ios", "android", "security", "compliance", "hr", "recruiter",
    "finance", "accountant", "legal", "customer", "success", "operations",
]


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_company_from_title(title: str) -> tuple[str, str]:
    """Try to extract company name from title using common separators.
    
    Returns (company, cleaned_title).
    Handles formats like:
      "Company | Role"  "Company - Role"  "Company: Role"
      "Company – Role"  "Company: Role (Remote)"
    Also catches cases where title starts with a company-looking word
    followed by a known job keyword, e.g. "Acme hiring Engineer".
    """
    # Try common separators first (|  -  :  –  ·)
    for sep in [" | ", " - ", " – ", " · ", " — ", " : "]:
        if sep in title:
            parts = title.split(sep, 1)
            if len(parts) == 2:
                c, t = parts[0].strip(), parts[1].strip()
                if len(c) < 80 and len(t) > 5:
                    return c, t

    # Try "Company: Role"  (colon without spaces is common in RSS feeds)
    if ":" in title:
        parts = title.split(":", 1)
        if len(parts) == 2:
            c, t = parts[0].strip(), parts[1].strip()
            if len(c) < 80 and len(t) > 5:
                # Avoid splitting on URL schemes
                if "http" not in c.lower():
                    return c, t

    # Try splitting on " – " (em-dash)
    if "–" in title:
        parts = title.split("–", 1)
        c, t = parts[0].strip(), parts[1].strip()
        if len(c) < 80 and len(t) > 5:
            return c, t

    return "", title


def _extract_salary_from_text(text: str) -> str:
    """Extract salary string from description text."""
    if not text:
        return ""
    # Match patterns like "$80k-120k", "$100,000 - $150,000", "€50K", "£70k"
    patterns = [
        r'[\$€£]\s*[\d,]+(?:k|K)?(?:\s*[-–to]+\s*[\$€£]?\s*[\d,]+(?:k|K)?)?',
        r'\d[\d,]*\s*[-–to]+\s*\d[\d,]*\s*(?:USD|EUR|GBP)?',
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return m.group(0)
    return ""


def _detect_location_from_entry(entry) -> Optional[str]:
    """Try to extract location from RSS entry tags/categories."""
    # Check tags/categories
    for tag_field in ("tags", "categories", "subjects"):
        tags = getattr(entry, tag_field, None)
        if tags:
            for t in tags:
                label = ""
                if isinstance(t, str):
                    label = t
                elif hasattr(t, "label"):
                    label = t.label or t.get("term", "") if hasattr(t, "get") else ""
                elif hasattr(t, "term"):
                    label = t.term
                label_lower = label.lower()
                if any(loc in label_lower for loc in ("remote", "worldwide", "global", "anywhere")):
                    return "Remote"
                if any(loc in label_lower for loc in ("europe", "uk", "usa", "canada", "asia", "india")):
                    return label
    return None


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

            # Company: try author first, then extract from title
            company = (entry.author or "") if hasattr(entry, "author") and entry.author else ""
            if not company:
                company, title = _extract_company_from_title(title)

            # Location: try tags/categories, then default
            location = self.default_location
            detected_loc = _detect_location_from_entry(entry)
            if detected_loc:
                location = detected_loc

            # Salary: extract from description
            salary = _extract_salary_from_text(description)

            external_id = self.make_external_id(self.name, link, title)
            jobs.append(
                RawJob(
                    external_id=external_id,
                    source=self.name,
                    title=title,
                    company=company or "Unknown",
                    url=link,
                    description=description,
                    location=location,
                    salary=salary,
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
            feed_url="https://www.workingnomads.com/jobs/feed",
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


class CryptoJobsScraper(RSSScraper):
    """CryptoJobsList — blockchain and web3 roles."""

    def __init__(self):
        super().__init__(
            name="cryptojobs",
            feed_url="https://cryptojobslist.com/rss/remote-jobs.xml",
            default_location="Remote",
        )


class EuroperemotelyScraper(RSSScraper):
    """EuropeRemotely — remote jobs within European timezones."""

    def __init__(self):
        super().__init__(
            name="europeremotely",
            feed_url="https://europeremotely.com/feed/",
            default_location="Europe / Remote",
        )


class RemoteCoUkScraper(RSSScraper):
    """Remote.co.uk — UK-focused remote jobs."""

    def __init__(self):
        super().__init__(
            name="remotecouk",
            feed_url="https://remote.co.uk/jobs/feed/",
            default_location="UK / Remote",
        )


class SkipTheDriveScraper(RSSScraper):
    """SkipTheDrive — remote job aggregator."""

    def __init__(self):
        super().__init__(
            name="skipthedrive",
            feed_url="https://www.skipthedrive.com/feed/",
            default_location="Remote",
        )


# === New RSS scrapers for broader coverage ===

class RemoteIndexScraper(RSSScraper):
    """RemoteIndex — curated remote jobs."""

    def __init__(self):
        super().__init__(
            name="remoteindex",
            feed_url="https://remoteindex.co/feed.xml",
            default_location="Remote",
        )


class RemotelyScraper(RSSScraper):
    """Remotely — remote job board."""

    def __init__(self):
        super().__init__(
            name="remotely",
            feed_url="https://remotely.jobs/feed/",
            default_location="Remote",
        )


class Remote4MeScraper(RSSScraper):
    """Remote4Me — remote job aggregator."""

    def __init__(self):
        super().__init__(
            name="remote4me",
            feed_url="https://remote4me.com/feed/",
            default_location="Remote",
        )


class FourDayWeekScraper(RSSScraper):
    """4DayWeek — 4-day work week jobs."""

    def __init__(self):
        super().__init__(
            name="4dayweek",
            feed_url="https://4dayweek.io/feed",
            default_location="Remote",
        )


class RemotersScraper(RSSScraper):
    """Remoters — remote jobs board."""

    def __init__(self):
        super().__init__(
            name="remoters",
            feed_url="https://remoters.net/feed/",
            default_location="Remote",
        )


class LandingJobsScraper(RSSScraper):
    name = "landingjobs"

    def __init__(self):
        super().__init__(
            name="landingjobs",
            feed_url="https://landing.jobs/feed",
            default_location="Remote",
        )


class RealWorkFromAnywhereScraper(RSSScraper):
    name = "realworkfromanywhere"

    def __init__(self):
        super().__init__(
            name="realworkfromanywhere",
            feed_url="https://www.realworkfromanywhere.com/rss.xml",
            default_location="Remote",
        )


# === Phase 5: New RSS scrapers ===

class RelocateMeScraper(RSSScraper):
    """Relocate.me — jobs with visa sponsorship."""

    def __init__(self):
        super().__init__(
            name="relocateme",
            feed_url="https://relocate.me/feed",
            default_location="Remote / Visa Sponsorship",
        )


class CraigslistRemoteScraper(RSSScraper):
    """Craigslist — US-wide remote job listings."""

    def __init__(self):
        super().__init__(
            name="craigslist",
            feed_url="https://geo.craigslist.org/iso/us/search/jjj?query=remote&format=rss",
            default_location="US / Remote",
        )


class EuropeRemoteComScraper(RSSScraper):
    """EuropeRemote.com — European remote jobs (distinct from europeremotely)."""

    def __init__(self):
        super().__init__(
            name="europeremotecom",
            feed_url="https://europeremote.com/jobs/rss",
            default_location="Europe / Remote",
        )


class HireWeb3Scraper(RSSScraper):
    """HireWeb3 — Web3 and blockchain remote jobs."""

    def __init__(self):
        super().__init__(
            name="hireweb3",
            feed_url="https://hireweb3.io/job/rss",
            default_location="Remote",
        )
