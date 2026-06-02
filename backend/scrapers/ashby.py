"""Ashby public API scraper — parallel company fetch with timeout."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

ASHBY_API = "https://api.ashbyhq.com/posting-api/job-board"

# Only companies with high likelihood of DevOps/engineering remote roles
# Removed dead slugs that return 404 (scaleai, anthropic, together, etc.)
KNOWN_COMPANIES: Dict[str, str] = {
    "snowflake": "Snowflake",
    "notion": "Notion",
    "vanta": "Vanta",
    "ramp": "Ramp",
    "replit": "Replit",
    "cursor": "Cursor",
    "uipath": "UiPath",
    "deel": "Deel",
    "openai": "OpenAI",
    "netgear": "Netgear",
    "lemonade": "Lemonade",
    "eightsleep": "Eight Sleep",
    "gorgias": "Gorgias",
    "linear": "Linear",
    "zapier": "Zapier",
    "hackerone": "HackerOne",
    "coder": "Coder",
    "posthog": "PostHog",
    "sequoia": "Sequoia",
    "fullstory": "FullStory",
    "mercury": "Mercury",
    "marqeta": "Marqeta",
    "reddit": "Reddit",
    "railway": "Railway",
    "plaid": "Plaid",
    "perplexity": "Perplexity",
    "cohere": "Cohere",
    "modal": "Modal",
    "pinecone": "Pinecone",
    "weaviate": "Weaviate",
    "raycast": "Raycast",
    "warp": "Warp",
    "loom": "Loom",
}


class AshbyScraper(BaseScraper):
    """Ashby ATS public API scraper — parallel company fetch with 30s hard timeout."""

    name = "ashby"
    ASHBY_TIMEOUT = 30  # seconds — return whatever we have after this

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        seen_ids: set = set()
        seen_lock = __import__("threading").Lock()
        start_time = time.time()

        def _fetch_company(slug: str, display_name: str) -> List[RawJob]:
            if time.time() - start_time > self.ASHBY_TIMEOUT:
                return []
            url = f"{ASHBY_API}/{slug}?includeCompensation=true"
            if criteria and criteria.query:
                url += f"&query={criteria.query.replace(' ', '%20')}"
            try:
                resp = self.fetch(url)
                if resp.status_code != 200:
                    return []
                data = resp.json()
            except Exception:
                return []
            items = data.get("jobs", [])
            if not items:
                return []
            local_jobs = []
            for item in items:
                if not item.get("isListed", False):
                    continue
                title = item.get("title", "").strip()
                if not title:
                    continue
                job_url = item.get("jobUrl", "")
                apply_url = item.get("applyUrl", "")
                if apply_url and not job_url:
                    job_url = apply_url
                description = item.get("descriptionPlain", "") or ""
                desc_html = item.get("descriptionHtml", "")
                if not description and desc_html:
                    description = desc_html
                location = item.get("location", "") or ""
                if not location and item.get("address", {}).get("postalAddress", {}):
                    addr = item["address"]["postalAddress"]
                    parts = []
                    if addr.get("addressLocality"):
                        parts.append(addr["addressLocality"])
                    if addr.get("addressRegion"):
                        parts.append(addr["addressRegion"])
                    if addr.get("addressCountry"):
                        parts.append(addr["addressCountry"])
                    if parts:
                        location = ", ".join(parts)
                if not location and item.get("isRemote"):
                    location = "Remote"
                workplace = item.get("workplaceType", "")
                if workplace:
                    description = f"{description}\nWorkplace: {workplace}" if description else f"Workplace: {workplace}"
                salary = ""
                comp = item.get("compensation", {})
                if comp:
                    summary = comp.get("compensationTierSummary", "")
                    salary_summary = comp.get("scrapeableCompensationSalarySummary", "")
                    salary = salary_summary or summary or (tiers[0].get("tierSummary", "") if comp.get("compensationTiers") else "")
                posted_at = str(item.get("publishedAt", "")) or ""
                external_id = self.make_external_id(self.name, job_url, title)
                with seen_lock:
                    if external_id in seen_ids:
                        continue
                    seen_ids.add(external_id)
                local_jobs.append(
                    RawJob(
                        external_id=external_id,
                        source=self.name,
                        title=title,
                        company=display_name,
                        url=job_url,
                        description=description,
                        location=location or "Remote",
                        salary=salary,
                        posted_at=posted_at,
                    )
                )
            return local_jobs

        # Fetch companies in parallel with a hard timeout
        workers = min(len(KNOWN_COMPANIES), 10)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_fetch_company, slug, name): slug for slug, name in KNOWN_COMPANIES.items()}
            for fut in as_completed(futures, timeout=self.ASHBY_TIMEOUT):
                try:
                    jobs.extend(fut.result())
                except Exception:
                    pass

        logger.info("Ashby: %d jobs from %d companies in %.0fs", len(jobs), len(KNOWN_COMPANIES), time.time() - start_time)
        return jobs
