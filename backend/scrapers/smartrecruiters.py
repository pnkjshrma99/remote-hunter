"""SmartRecruiters public API scraper.

SmartRecruiters provides a public JSON API endpoint per company.
No authentication required for reading public postings.
"""

import logging
from typing import Dict, List

import httpx

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

KNOWN_COMPANIES: Dict[str, str] = {
    "equinox": "Equinox",
    "visa": "Visa",
    "autodesk": "Autodesk",
    "vmware": "VMware",
    "intuit": "Intuit",
    "ebay": "eBay",
    "twilio": "Twilio",
    "airbnb": "Airbnb",
    "pinterest": "Pinterest",
    "square": "Square",
    "zillow": "Zillow",
    "roblox": "Roblox",
    "snapchat": "Snap Inc.",
    "walmart": "Walmart",
    "adidas": "Adidas",
    "american-express": "American Express",
    "att": "AT&T",
    "booking": "Booking.com",
    "capgemini": "Capgemini",
    "coca-cola": "Coca-Cola",
    "dyson": "Dyson",
    "fedex": "FedEx",
    "genpact": "Genpact",
    "hilton": "Hilton",
    "hsbc": "HSBC",
    "ibm": "IBM",
    "johnson-johnson": "Johnson & Johnson",
    "kpmg": "KPMG",
    "mastercard": "Mastercard",
    "mc-donalds": "McDonald's",
    "microsoft": "Microsoft",
    "nike": "Nike",
    "oracle": "Oracle",
    "pepsico": "PepsiCo",
    "procter-gamble": "Procter & Gamble",
    "sap": "SAP",
    "seimens": "Siemens",
    "tesla": "Tesla",
    "unilever": "Unilever",
    "united-health-group": "UnitedHealth Group",
    "wells-fargo": "Wells Fargo",
}


class SmartRecruitersScraper(BaseScraper):
    """SmartRecruiters ATS public API scraper."""

    name = "smartrecruiters"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        seen_ids: set = set()

        for slug, display_name in KNOWN_COMPANIES.items():
            url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
            try:
                with httpx.Client(timeout=10, follow_redirects=True) as client:
                    resp = client.get(url)
                if resp.status_code != 200:
                    logger.debug("SmartRecruiters '%s' returned %s", slug, resp.status_code)
                    continue
                data = resp.json()
            except Exception as e:
                logger.debug("SmartRecruiters '%s' error: %s", slug, e)
                continue

            for item in data.get("content", data if isinstance(data, list) else []):
                title = (item.get("name") or item.get("title", "")).strip()
                if not title:
                    continue

                job_id = str(item.get("id", ""))
                ext_id = self.make_external_id(self.name, f"{slug}-{job_id}", title)
                if ext_id in seen_ids:
                    continue
                seen_ids.add(ext_id)

                location_obj = item.get("location", {}) or {}
                location = location_obj.get("city", "") or location_obj.get("country", "") or ""

                description = (item.get("jobAd", {}) or {}).get("sections", {})
                description_text = ""
                for section in description.get("jobDescription", []):
                    description_text += (section.get("text", "") or section.get("content", "") or "") + "\n"

                jobs.append(
                    RawJob(
                        external_id=ext_id,
                        source=f"{self.name}:{slug}",
                        title=title,
                        company=display_name,
                        url=item.get("applyUrl", "") or item.get("url", ""),
                        description=description_text.strip(),
                        location=location or "Remote",
                        posted_at=item.get("postedDate", "") or item.get("createdDate", ""),
                    )
                )

        logger.info("SmartRecruiters: %d jobs from %d companies", len(jobs), len(KNOWN_COMPANIES))
        return jobs
