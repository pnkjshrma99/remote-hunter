"""Base scraper with rate limiting, ethical fetching, auth detection, and health checks."""

import hashlib
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

import httpx
from fake_useragent import UserAgent
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)

from app.config import get_settings
from scrapers.filters import RawJob, passes_all_filters
from scrapers.schemas import SearchCriteria, NormalizedJob

logger = logging.getLogger(__name__)
settings = get_settings()
_ua = UserAgent()


class AuthRequiredError(Exception):
    """Raised when a scraper encounters an auth wall, login page, or captcha."""


AUTH_CHALLENGE_PATTERNS = [
    r"(?i)sign\s*in",
    r"(?i)log\s*in",
    r"(?i)login",
    r"(?i)signin",
    r"(?i)authenticate",
    r"(?i)captcha",
    r"(?i)recaptcha",
    r"(?i)hcaptcha",
    r"(?i)turnstile",
    r"(?i)challenge",
    r"(?i)access denied",
    r"(?i)accessdenied",
    r"(?i)blocked",
    r"(?i)too many requests",
    r"(?i)rate.li",
    r"(?i)cf-ray",
    r"(?i)cf-browser-verification",
    r"(?i)just a moment",
    r"(?i)checking your browser",
    r"(?i)verifying you are human",
    r"(?i)are you a robot",
    r"(?i)please verify",
    r"(?i)_cf_challenge",
    r"(?i)robot.or.human",
]


def _is_auth_page(response: httpx.Response) -> bool:
    """Check if the response is an auth wall, login page, or captcha challenge."""
    if response.status_code in (401, 403, 451):
        return True
    if response.status_code == 302 and "login" in response.headers.get("location", "").lower():
        return True

    # Skip content-type checks for non-HTML responses (RSS, JSON, etc.)
    ct = response.headers.get("content-type", "").lower()
    if "xml" in ct or "json" in ct or "atom" in ct or "rss" in ct:
        return False
    if not ("html" in ct or "text" in ct):
        return False

    text = response.text[:5000].lower()
    count = sum(1 for p in AUTH_CHALLENGE_PATTERNS if re.search(p, text))
    return count >= 2


@dataclass
class ScraperHealth:
    """Health status of a scraper."""
    name: str
    enabled: bool
    last_run: Optional[float] = None
    last_error: Optional[str] = None
    error_count: int = 0
    success_count: int = 0
    total_jobs: int = 0
    
    def is_healthy(self) -> bool:
        """Check if scraper is healthy (less than 5 consecutive errors)."""
        return self.error_count < 5


class BaseScraper(ABC):
    name: str = "base"
    enabled: bool = True
    max_retries: int = 0

    def __init__(self):
        self._last_request = 0.0
        self.health = ScraperHealth(name=self.name, enabled=self.enabled)

    def _headers(self) -> dict:
        return {
            "User-Agent": _ua.random,
            "Accept": "application/json, text/html, application/xml, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
        }

    def _rate_limit(self):
        delay = settings.request_delay_seconds
        if delay <= 0:
            return
        elapsed = time.time() - self._last_request
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_request = time.time()

    @retry(
        stop=stop_after_attempt(1),
        wait=wait_exponential(multiplier=1, min=0, max=1),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.ReadError)),
        reraise=True,
    )
    def fetch(self, url: str, **kwargs) -> httpx.Response:
        """Fetch URL with exponential backoff retry on network errors."""
        self._rate_limit()
        try:
            with httpx.Client(
                timeout=settings.request_timeout_seconds,
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=5),
            ) as client:
                response = client.get(url, headers=self._headers(), **kwargs)
                # Check for auth challenges before raise_for_status
                if _is_auth_page(response):
                    raise AuthRequiredError(
                        f"{self.name}: Auth required when fetching {url} "
                        f"(status={response.status_code})"
                    )
                response.raise_for_status()
                return response
        except AuthRequiredError:
            raise
        except httpx.TimeoutException as e:
            logger.warning("%s: Timeout fetching %s after retries", self.name, url)
            raise
        except httpx.HTTPStatusError as e:
            logger.warning("%s: HTTP %d error fetching %s", self.name, e.response.status_code, url)
            raise
        except (httpx.ConnectError, httpx.ReadError) as e:
            logger.warning("%s: Connection error: %s", self.name, str(e))
            raise

    @staticmethod
    def make_external_id(source: str, url: str, title: str = "") -> str:
        key = f"{source}:{url or title}"
        return hashlib.sha256(key.encode()).hexdigest()[:32]

    @abstractmethod
    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        pass
    
    def get_source_params(self, criteria: SearchCriteria | None = None) -> Dict[str, Any]:
        """
        Get source-specific query parameters for filtering at the source.
        
        Override this in subclasses to implement source-side filtering.
        This allows scrapers to filter jobs before fetching, reducing bandwidth
        and improving performance.
        
        Args:
            criteria: Search criteria
            
        Returns:
            Dictionary of query parameters for the source API
        """
        if criteria:
            # Handle both SearchCriteria versions (filters.py vs schemas.py)
            if hasattr(criteria, 'to_source_params'):
                return criteria.to_source_params()
            return criteria.__dict__ if hasattr(criteria, '__dict__') else {}
        return {}

    def run(
        self,
        strict_junior: bool = False,
        criteria: SearchCriteria | None = None,
    ) -> List[RawJob]:
        if not self.enabled:
            logger.debug("%s: Scraper disabled", self.name)
            return []
        
        try:
            criteria = criteria or SearchCriteria()
            raw = self.scrape(criteria=criteria)
            filtered = [
                j
                for j in raw
                if passes_all_filters(j, strict_junior=strict_junior, criteria=criteria)
            ]
            
            # Update health metrics
            self.health.success_count += 1
            self.health.total_jobs = len(filtered)
            self.health.last_run = time.time()
            self.health.last_error = None
            
            logger.info("%s: %d raw -> %d filtered", self.name, len(raw), len(filtered))
            return filtered
            
        except AuthRequiredError as e:
            self.health.error_count += 1
            self.health.last_error = f"AuthRequiredError: {str(e)}"
            logger.warning("%s: %s", self.name, self.health.last_error)
            return []
            
        except RetryError as e:
            self.health.error_count += 1
            self.health.last_error = f"RetryError after {self.max_retries} attempts: {str(e)}"
            logger.error("%s: %s", self.name, self.health.last_error)
            return []
            
        except httpx.HTTPStatusError as e:
            self.health.error_count += 1
            self.health.last_error = f"HTTP {e.response.status_code}: {str(e)}"
            logger.warning("%s: %s", self.name, self.health.last_error)
            return []
            
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
            self.health.error_count += 1
            self.health.last_error = f"{type(e).__name__}: {str(e)}"
            logger.warning("%s: Network error - %s", self.name, self.health.last_error)
            return []
            
        except Exception as e:
            self.health.error_count += 1
            self.health.last_error = str(e)
            logger.exception("%s: Unexpected error", self.name)
            return []
