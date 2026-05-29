"""Cookie/session management for auth-gated scrapers.

Provides persistent cookie storage and login workflows for job boards
that require authentication to scrape.
"""

import json
import logging
import os
import pickle
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import httpx

from scrapers.base import AuthRequiredError

logger = logging.getLogger(__name__)

DEFAULT_COOKIE_DIR = Path("data/cookies")


@dataclass
class CredentialStore:
    """Manages credentials for authenticated scrapers."""
    linkedin_email: str = ""
    linkedin_password: str = ""
    naukri_email: str = ""
    naukri_password: str = ""
    glassdoor_email: str = ""
    glassdoor_password: str = ""

    @classmethod
    def from_settings(cls) -> "CredentialStore":
        """Load credentials from app settings or env."""
        try:
            from app.config import get_settings
            s = get_settings()
            return cls(
                linkedin_email=s.linkedin_email,
                linkedin_password=s.linkedin_password,
                naukri_email=s.naukri_email,
                naukri_password=s.naukri_password,
                glassdoor_email=s.glassdoor_email,
                glassdoor_password=s.glassdoor_password,
            )
        except Exception:
            return cls()

    def has_credentials(self, source: str) -> bool:
        """Check if credentials are available for a source."""
        email = getattr(self, f"{source}_email", "")
        password = getattr(self, f"{source}_password", "")
        return bool(email and password)

    def get(self, source: str) -> tuple[str, str]:
        """Get (email, password) for a source."""
        email = getattr(self, f"{source}_email", "")
        password = getattr(self, f"{source}_password", "")
        return email, password


@dataclass
class CookieSession:
    """Persistent HTTP session with cookie storage for a scraper."""

    source: str
    cookies: Dict[str, str] = field(default_factory=dict)
    last_login: float = 0.0
    cookie_file: Path = None
    _client: Optional[httpx.Client] = None

    def __post_init__(self):
        if self.cookie_file is None:
            DEFAULT_COOKIE_DIR.mkdir(parents=True, exist_ok=True)
            self.cookie_file = DEFAULT_COOKIE_DIR / f"{self.source}_cookies.pkl"

    @property
    def is_logged_in(self) -> bool:
        """Check if session has recent cookies."""
        if not self.cookies:
            return False
        age = time.time() - self.last_login
        return age < 86400  # Re-login every 24 hours

    def save(self):
        """Persist cookies to disk."""
        self.cookie_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "cookies": self.cookies,
            "last_login": self.last_login,
            "source": self.source,
        }
        with open(self.cookie_file, "wb") as f:
            pickle.dump(data, f)
        logger.debug(f"Saved {len(self.cookies)} cookies for {self.source}")

    def load(self) -> bool:
        """Load persisted cookies from disk. Returns True if loaded."""
        if not self.cookie_file.exists():
            return False
        try:
            with open(self.cookie_file, "rb") as f:
                data = pickle.load(f)
            self.cookies = data.get("cookies", {})
            self.last_login = data.get("last_login", 0.0)
            logger.debug(f"Loaded {len(self.cookies)} cookies for {self.source}")
            return bool(self.cookies)
        except Exception as e:
            logger.warning(f"Failed to load cookies for {self.source}: {e}")
            return False

    def clear(self):
        """Clear saved cookies."""
        self.cookies = {}
        self.last_login = 0.0
        if self.cookie_file.exists():
            self.cookie_file.unlink()

    def get_client(self) -> httpx.Client:
        """Get an httpx Client with stored cookies pre-set."""
        if self._client is None:
            self._client = httpx.Client(
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=5),
            )
            if self.cookies:
                for name, value in self.cookies.items():
                    self._client.cookies.set(name, value)
        return self._client

    def extract_from_response(self, response: httpx.Response):
        """Extract cookies from a response after login."""
        for cookie in response.cookies.jar:
            self.cookies[cookie.name] = cookie.value
        self.last_login = time.time()
        self.save()

    def close(self):
        if self._client:
            self._client.close()
            self._client = None


class AuthenticatedScraperMixin:
    """Mixin for scrapers that need authentication.

    Provides a cookie-based session system with persistent storage.
    Subclasses must implement `login()` and set `self.auth_source`.
    """

    auth_source: str = ""
    _session: Optional[CookieSession] = None
    _credentials: Optional[CredentialStore] = None

    @property
    def session(self) -> CookieSession:
        if self._session is None:
            self._session = CookieSession(source=self.auth_source)
            self._session.load()
        return self._session

    @property
    def credentials(self) -> CredentialStore:
        if self._credentials is None:
            self._credentials = CredentialStore.from_settings()
        return self._credentials

    def ensure_login(self) -> bool:
        """Ensure we have valid login cookies. Returns True if logged in."""
        if self.session.is_logged_in:
            logger.debug(f"{self.auth_source}: Using existing session")
            return True

        if not self.credentials.has_credentials(self.auth_source):
            logger.warning(
                f"{self.auth_source}: No credentials configured. "
                f"Set {self.auth_source}_email and {self.auth_source}_password env vars."
            )
            return False

        logger.info(f"{self.auth_source}: Attempting login...")
        try:
            self.login()
            self.session.extract_from_response(self._login_response)
            logger.info(f"{self.auth_source}: Login successful")
            return True
        except Exception as e:
            logger.error(f"{self.auth_source}: Login failed: {e}")
            self.session.clear()
            return False

    def login(self):
        """Implement in subclass - performs login and stores cookies."""
        raise NotImplementedError

    def close(self):
        if self._session:
            self._session.close()
