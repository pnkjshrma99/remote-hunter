"""Remote.co scraper using stealth browser automation.

Remote.co uses Cloudflare anti-scraping protection which blocks
simple httpx requests with 403. This scraper uses Playwright
with stealth mode to bypass these protections.

If Playwright is not installed, falls back to httpx with
realistic browser headers.
"""

import logging
import re
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

REMOTECO_URL = "https://remote.co/remote-jobs/"


class RemoteCoScraper(BaseScraper):
    name = "remoteco"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape Remote.co jobs using stealth browser automation."""
        jobs: List[RawJob] = []
        
        # Strategy 1: Try Playwright with stealth (bypasses Cloudflare)
        playwright_jobs = self._scrape_with_playwright(criteria)
        if playwright_jobs:
            logger.info(f"Playwright returned {len(playwright_jobs)} jobs")
            return playwright_jobs
        
        # Strategy 2: Fallback to direct HTTP with aggressive headers
        logger.info("Playwright unavailable, trying HTTP fallback")
        http_jobs = self._scrape_with_http(criteria)
        if http_jobs:
            return http_jobs
        
        # Strategy 3: Alternative - scrape Remote.co's JSON API if available
        logger.info("HTTP fallback failed, trying JSON API")
        api_jobs = self._scrape_json_api(criteria)
        return api_jobs if api_jobs else []

    def _scrape_with_playwright(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Use Playwright with stealth to bypass Cloudflare."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("Playwright not installed. Install with: pip install playwright")
            return []
        
        jobs: List[RawJob] = []
        try:
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
                    extra_http_headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate, br",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Sec-Fetch-User": "?1",
                    }
                )
                page = context.new_page()
                
                # Navigate with extended timeout and wait for content
                page.goto(REMOTECO_URL, wait_until="networkidle", timeout=30000)
                
                # Wait for actual job content to appear
                page.wait_for_selector("a.card, .job-card, .job-listing, article", timeout=15000)
                
                # Get all job links
                job_links = page.query_selector_all("a.card.m-0")
                
                for link in job_links:
                    try:
                        href = link.get_attribute("href")
                        if not href:
                            continue
                        if not href.startswith("http"):
                            href = f"https://remote.co{href}"
                        
                        # Extract title
                        title_el = link.query_selector("h2, .title, h3")
                        title = title_el.text_content().strip() if title_el else ""
                        
                        # Extract company
                        company_el = link.query_selector("p.m-0, .company, .text-secondary")
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
                    except Exception as e:
                        continue
                
                browser.close()
            
        except Exception as e:
            logger.warning(f"Playwright scrape failed: {e}")
        
        return jobs

    def _scrape_with_http(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Fallback: direct HTTP with realistic browser headers."""
        jobs: List[RawJob] = []
        try:
            # Use a single custom User-Agent header via the base class
            # DO NOT pass 'headers' param - base.fetch() already adds its own headers
            resp = self.fetch(REMOTECO_URL)
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            
            job_cards = soup.find_all("a", class_="card")
            if not job_cards:
                job_cards = soup.select("a[href*='/remote-jobs/']")
            
            seen = set()
            for card in job_cards:
                try:
                    href = card.get("href", "")
                    if "/remote-jobs/" not in href:
                        continue
                    if not href.startswith("http"):
                        href = f"https://remote.co{href}"
                    
                    title_el = card.find("h2") or card.find("h3") or card.find("h4")
                    title = title_el.get_text(strip=True) if title_el else ""
                    
                    company_el = card.find("p", class_="text-secondary") or card.find("p", class_="m-0")
                    company = company_el.get_text(strip=True) if company_el else "Unknown"
                    
                    if not title or title in seen:
                        continue
                    seen.add(title)
                    
                    external_id = self.make_external_id(self.name, href, title)
                    jobs.append(
                        RawJob(
                            external_id=external_id,
                            source=self.name,
                            title=title,
                            company=company,
                            url=href,
                            location="Remote",
                        )
                    )
                except Exception as e:
                    continue
            
        except Exception as e:
            logger.warning(f"HTTP scrape failed: {e}")
        
        return jobs

    def _scrape_json_api(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Alternative: try to scrape via JSON endpoint if available."""
        jobs: List[RawJob] = []
        try:
            # Some job boards provide JSON feeds
            json_urls = [
                "https://remote.co/wp-json/wp/v2/jobs?per_page=50",
                "https://remote.co/wp-json/wp/v2/posts?per_page=50",
            ]
            
            for json_url in json_urls:
                try:
                    resp = self.fetch(json_url)
                    data = resp.json()
                    
                    for item in data if isinstance(data, list) else data.get("data", []):
                        title = item.get("title", {}) if isinstance(item.get("title"), dict) else item.get("title", "")
                        if isinstance(title, dict):
                            title = title.get("rendered", "")
                        
                        content = item.get("content", {}) if isinstance(item.get("content"), dict) else item.get("excerpt", "")
                        if isinstance(content, dict):
                            description = re.sub(r"<[^>]+>", " ", content.get("rendered", ""))
                        else:
                            description = ""
                        
                        link = item.get("link", "")
                        if not title:
                            continue
                        
                        external_id = self.make_external_id(self.name, link, title)
                        jobs.append(
                            RawJob(
                                external_id=external_id,
                                source=self.name,
                                title=title,
                                company="Unknown",
                                url=link,
                                description=description.strip(),
                                location="Remote",
                            )
                        )
                    
                    if jobs:
                        break
                except Exception:
                    continue
            
        except Exception as e:
            logger.warning(f"JSON API scrape failed: {e}")
        
        return jobs