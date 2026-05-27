"""GitHub Jobs Scraper

Fetches jobs from GitHub using the public Issues API.
Uses a single simple search query instead of brute-forcing
multiple repos and labels (which hits rate limits fast).

Rate limit: 60 req/hr without auth, 5000 req/hr with GitHub token.
"""

import logging
import re
from typing import List, Optional
from urllib.parse import quote

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)


class GitHubJobsScraper(BaseScraper):
    name = "github_jobs"
    API_URL = "https://api.github.com"
    
    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Search GitHub Issues for remote job postings (single API call)."""
        jobs: List[RawJob] = []
        
        try:
            # Single search: look for remote+job+hiring across all of GitHub
            search_query = "remote+job+hiring"
            if criteria and criteria.query:
                terms = criteria.query.split()
                search_terms = "+".join(terms[:2])
                search_query = f"remote+{search_terms}+hiring+job"
            
            encoded_q = quote(
                f"is:issue is:open label:job \"{search_query}\" comments:>0 "
            )
            api_url = f"{self.API_URL}/search/issues?q={encoded_q}&per_page=20&sort=created"
            
            resp = self.fetch(api_url)
            data = resp.json()
            
            for item in data.get("items", []):
                title = item.get("title", "")
                body = item.get("body", "") or ""
                html_url = item.get("html_url", "")
                
                # Check it's actually a job posting with remote
                combined = f"{title} {body}".lower()
                if not ("remote" in combined or "hiring" in combined):
                    continue
                
                company = self._extract_company(title, body)
                
                external_id = self.make_external_id(self.name, html_url, title)
                jobs.append(
                    RawJob(
                        external_id=external_id,
                        source=self.name,
                        title=title,
                        company=company,
                        url=html_url,
                        description=body[:800],
                        location="Remote",
                        posted_at=item.get("created_at", ""),
                    )
                )
            
            logger.info(f"GitHub Jobs: {len(jobs)} jobs (1 API call)")
            
        except Exception as e:
            logger.error(f"GitHub Jobs failed: {e}")
        
        return jobs

    def _extract_company(self, title: str, description: str) -> str:
        """Try to extract company name from title or description."""
        combined = f"{title} {description}"
        patterns = [
            r"^([\w\s.]+)\s+(?:is|are)\s+hiring",
            r"^([\w\s.]+)\s*[:\-–—]\s*.+",
            r"(?:at|@)\s+([A-Z][A-Za-z0-9\s.]+?)(?:\s+is|\s+in|\s+for|\s+we|\s+as|\s+\.|$)",
            r"(?:company|organization):\s*([A-Za-z0-9\s.]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, combined, re.I)
            if match:
                company = match.group(1).strip()
                if 2 < len(company) < 50:
                    return company
        return "Unknown"