"""Wellfound (AngelList) Jobs Scraper

Fetches jobs from Wellfound (formerly AngelList) public website.
The GraphQL API requires authentication, so we scrape the public
HTML/JSON pages instead, with Playwright as the primary strategy.

Wellfound is aggressively anti-scraping. The public JSON endpoints
are often blocked. Playwright may work but requires installation.
"""

import logging
import re
from typing import List, Optional
from scrapers.base import AuthRequiredError, BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)


class WellfoundScraper(BaseScraper):
    """Wellfound (AngelList) job scraper using public web scraping."""

    name = "wellfound"
    BASE_URL = "https://wellfound.com"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape jobs from Wellfound public website."""
        jobs: List[RawJob] = []

        # Strategy 1: Try Playwright for JS-rendered content
        try:
            from playwright.sync_api import sync_playwright
            jobs = self._scrape_with_playwright(criteria)
            if jobs:
                logger.info(f"Playwright returned {len(jobs)} jobs from Wellfound")
                return jobs
        except ImportError:
            logger.debug("Playwright not available for Wellfound")

        # Strategy 2: Try public JSON API endpoint
        api_jobs = self._scrape_public_api(criteria)
        if api_jobs:
            logger.info(f"API returned {len(api_jobs)} jobs from Wellfound")
            return api_jobs

        logger.warning("All scraping strategies failed for Wellfound")
        return jobs

    def _scrape_with_playwright(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape Wellfound using Playwright with stealth."""
        jobs: List[RawJob] = []
        try:
            from playwright.sync_api import sync_playwright

            search_query = "remote"
            if criteria and criteria.query:
                search_query = f"remote+{criteria.query.replace(' ', '+')}"

            url = f"{self.BASE_URL}/jobs?q={search_query}"

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                )
                page = context.new_page()

                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                except Exception as e:
                    logger.warning(f"Wellfound Playwright navigation failed: {e}")
                    browser.close()
                    return []

                page.wait_for_timeout(3000)

                for _ in range(3):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(1000)

                selectors = [
                    '[data-testid="job-card"]',
                    '[class*="job-card"]',
                    'a[href*="/jobs/"][class*="card"]',
                    'div[class*="styles__card"]',
                ]

                job_elements = []
                for selector in selectors:
                    elements = page.query_selector_all(selector)
                    if elements:
                        job_elements = elements
                        break

                for card in job_elements:
                    try:
                        href = card.get_attribute("href")
                        if not href or "/jobs/" not in href:
                            continue
                        if not href.startswith("http"):
                            href = f"https://wellfound.com{href}"

                        title_el = card.query_selector("h2, h3, [class*='title'], [class*='position']")
                        title = title_el.text_content().strip() if title_el else ""

                        company_el = card.query_selector("[class*='company'], [class*='org'], [class*='name']")
                        company = company_el.text_content().strip() if company_el else "Unknown"

                        if not title:
                            continue

                        external_id = self.make_external_id(self.name, href, title)
                        jobs.append(
                            RawJob(
                                external_id=external_id,
                                source=self.name,
                                title=title,
                                company=company,
                                url=href,
                                description="",
                                location="Remote",
                            )
                        )
                    except Exception:
                        continue

                browser.close()

        except Exception as e:
            logger.warning(f"Wellfound Playwright scrape failed: {e}")

        return jobs

    def _scrape_public_api(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Try Wellfound's public JSON endpoint."""
        jobs: List[RawJob] = []
        try:
            api_url = f"{self.BASE_URL}/jobs.json"
            if criteria and criteria.query:
                api_url += f"?query={criteria.query.replace(' ', '+')}"

            resp = self.fetch(api_url)
            data = resp.json()

            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("jobs", data.get("results", []))
            else:
                items = []

            for item in items:
                if not isinstance(item, dict):
                    continue

                title = item.get("title", "") or item.get("name", "")
                company = (item.get("company_name", "") or
                          item.get("company", {}).get("name", "") or
                          "Unknown")
                url = item.get("url", "") or item.get("absolute_url", "")
                if url and not url.startswith("http"):
                    url = f"https://wellfound.com{url}"

                if not title:
                    continue

                location = item.get("location") or item.get("location_type") or "Remote"
                if location and "remote" in str(location).lower():
                    location = "Remote"

                external_id = self.make_external_id(self.name, url, title)
                jobs.append(
                    RawJob(
                        external_id=external_id,
                        source=self.name,
                        title=title,
                        company=company,
                        url=url,
                        description=(item.get("description", "") or ""),
                        location=str(location),
                        salary=item.get("salary", "") or "",
                    )
                )

        except AuthRequiredError:
            logger.warning("Wellfound public API blocked - auth required")
            return []
        except Exception as e:
            logger.debug(f"Wellfound public API failed: {e}")

        return jobs
