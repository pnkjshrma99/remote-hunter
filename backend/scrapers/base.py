"""Base scraper with rate limiting and ethical fetching."""

import hashlib
import logging
import time
from abc import ABC, abstractmethod
from typing import List

import httpx
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from scrapers.filters import RawJob, SearchCriteria, passes_all_filters

logger = logging.getLogger(__name__)
settings = get_settings()
_ua = UserAgent()


class BaseScraper(ABC):
    name: str = "base"
    enabled: bool = True

    def __init__(self):
        self._last_request = 0.0

    def _headers(self) -> dict:
        return {
            "User-Agent": _ua.random,
            "Accept": "application/json, text/html, application/xml, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _rate_limit(self):
        elapsed = time.time() - self._last_request
        delay = settings.request_delay_seconds
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_request = time.time()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch(self, url: str, **kwargs) -> httpx.Response:
        self._rate_limit()
        with httpx.Client(timeout=settings.request_timeout_seconds, follow_redirects=True) as client:
            response = client.get(url, headers=self._headers(), **kwargs)
            response.raise_for_status()
            return response

    @staticmethod
    def make_external_id(source: str, url: str, title: str = "") -> str:
        key = f"{source}:{url or title}"
        return hashlib.sha256(key.encode()).hexdigest()[:32]

    @abstractmethod
    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        pass

    def run(
        self,
        strict_junior: bool = False,
        criteria: SearchCriteria | None = None,
    ) -> List[RawJob]:
        if not self.enabled:
            return []
        try:
            criteria = criteria or SearchCriteria()
            raw = self.scrape(criteria=criteria)
            filtered = [
                j
                for j in raw
                if passes_all_filters(j, strict_junior=strict_junior, criteria=criteria)
            ]
            logger.info("%s: %d raw -> %d filtered", self.name, len(raw), len(filtered))
            return filtered
        except Exception as e:
            logger.exception("Scraper %s failed: %s", self.name, e)
            return []
