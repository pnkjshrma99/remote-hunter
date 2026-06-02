"""Ashby public API scraper.

Uses Ashby's public job board API which returns structured job data
from companies using Ashby ATS (Linear, Ramp, Notion, OpenAI, etc.).
No authentication required.
"""

import logging
from typing import Dict, List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

ASHBY_API = "https://api.ashbyhq.com/posting-api/job-board"

# Slug -> Display name mapping
KNOWN_COMPANIES: Dict[str, str] = {
    "snowflake": "Snowflake",
    "harvey": "Harvey",
    "deliveroo": "Deliveroo",
    "notion": "Notion",
    "vanta": "Vanta",
    "ramp": "Ramp",
    "alan": "Alan",
    "replit": "Replit",
    "cursor": "Cursor",
    "uipath": "UiPath",
    "deel": "Deel",
    "openai": "OpenAI",
    "netgear": "Netgear",
    "lemonade": "Lemonade",
    "eightsleep": "Eight Sleep",
    "multiverse": "Multiverse",
    "gorgias": "Gorgias",
    "linear": "Linear",
    "zapier": "Zapier",
    "hackerone": "HackerOne",
    "coder": "Coder",
    "posthog": "PostHog",
    "sequoia": "Sequoia",
    "amo": "Amo",
    "january": "January",
    "aurorasolar": "Aurora Solar",
    "flock": "Flock",
    "fullstory": "FullStory",
    "formenergy": "Form Energy",
    "dave": "Dave",
    "claylabs": "Clay",
    "altura": "Altura",
    "infinite": "Infinite Lambda",
    "boomi": "Boomi",
    "convictional": "Convictional",
    "mercury": "Mercury",
    "marqeta": "Marqeta",
    "reddit": "Reddit",
    "railway": "Railway",
    "plaid": "Plaid",
    "scaleai": "Scale AI",
    "anthropic": "Anthropic",
    "perplexity": "Perplexity",
    "together": "Together AI",
    "cohere": "Cohere",
    "characterai": "Character.ai",
    "midjourney": "Midjourney",
    "runwayml": "Runway",
    "huggingface": "Hugging Face",
    "stabilityai": "Stability AI",
    "replicate": "Replicate",
    "modal": "Modal",
    "datum": "Datum",
    "pinecone": "Pinecone",
    "weaviate": "Weaviate",
    "chroma": "Chroma",
    "raycast": "Raycast",
    "warp": "Warp",
    "loom": "Loom",
    "descript": "Descript",
}


class AshbyScraper(BaseScraper):
    """Ashby ATS public API scraper — 2K+ jobs from 30+ top tech companies."""

    name = "ashby"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        seen_ids: set = set()

        for slug, display_name in KNOWN_COMPANIES.items():
            url = f"{ASHBY_API}/{slug}?includeCompensation=true"
            if criteria and criteria.query:
                url += f"&query={criteria.query.replace(' ', '%20')}"

            try:
                resp = self.fetch(url)
                if resp.status_code != 200:
                    logger.debug("Ashby slug '%s' returned %s — skipping", slug, resp.status_code)
                    continue
                data = resp.json()
            except Exception as e:
                logger.warning("Ashby fetch failed for '%s': %s", slug, e)
                continue

            items = data.get("jobs", [])
            if not items:
                logger.debug("Ashby slug '%s' returned 0 jobs", slug)
                continue

            for item in items:
                if not item.get("isListed", False):
                    continue

                title = item.get("title", "").strip()
                if not title:
                    continue

                company = display_name
                job_url = item.get("jobUrl", "")
                apply_url = item.get("applyUrl", "")
                if apply_url and not job_url:
                    job_url = apply_url

                # Description
                description = item.get("descriptionPlain", "") or ""
                desc_html = item.get("descriptionHtml", "")
                if not description and desc_html:
                    description = desc_html

                # Location
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

                # Workplace type
                workplace = item.get("workplaceType", "")
                if workplace:
                    if description:
                        description += f"\nWorkplace: {workplace}"
                    else:
                        description = f"Workplace: {workplace}"

                # Salary
                salary = ""
                comp = item.get("compensation", {})
                if comp:
                    summary = comp.get("compensationTierSummary", "")
                    salary_summary = comp.get("scrapeableCompensationSalarySummary", "")
                    if salary_summary:
                        salary = salary_summary
                    elif summary:
                        salary = summary
                    else:
                        tiers = comp.get("compensationTiers", [])
                        if tiers:
                            salary = tiers[0].get("tierSummary", "")

                posted_at = item.get("publishedAt", "")

                external_id = self.make_external_id(self.name, job_url, title)
                if external_id in seen_ids:
                    continue
                seen_ids.add(external_id)

                jobs.append(
                    RawJob(
                        external_id=external_id,
                        source=self.name,
                        title=title,
                        company=company,
                        url=job_url,
                        description=description,
                        location=location,
                        salary=salary,
                        posted_at=str(posted_at) if posted_at else "",
                    )
                )

        logger.info("Fetched %d jobs from Ashby API (%d companies)", len(jobs), len(KNOWN_COMPANIES))
        return jobs
