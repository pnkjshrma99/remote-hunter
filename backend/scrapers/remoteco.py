"""Remote.co scraper."""

import logging
from typing import List

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

REMOTECO_URL = "https://remote.co/remote-jobs/"


class RemoteCoScraper(BaseScraper):
    name = "remoteco"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        jobs: List[RawJob] = []
        try:
            resp = self.fetch(REMOTECO_URL)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            logger.warning("Remote.co fetch failed: %s", e)
            return []

        # Find all job cards
        job_cards = soup.find_all("a", class_="card m-0 border-0 shadow-sm")
        
        for card in job_cards:
            try:
                title = card.find("h2", class_="fs-5 mb-0")
                if not title:
                    continue
                title_text = title.get_text(strip=True)
                
                company_elem = card.find("p", class_="m-0 text-secondary small")
                company = company_elem.get_text(strip=True) if company_elem else "Unknown"
                
                url = card.get("href", "")
                if not url.startswith("http"):
                    url = f"https://remote.co{url}"
                
                # Get job details from the job page
                try:
                    job_resp = self.fetch(url)
                    job_soup = BeautifulSoup(job_resp.text, "html.parser")
                    
                    # Extract description
                    desc_div = job_soup.find("div", class_="job_description")
                    description = desc_div.get_text(strip=True) if desc_div else ""
                    
                    # Extract location
                    loc_elem = job_soup.find("span", class_="location")
                    location = loc_elem.get_text(strip=True) if loc_elem else "Remote"
                    
                    # Extract posted date
                    date_elem = job_soup.find("time")
                    posted_at = date_elem.get("datetime") if date_elem else None
                    
                except Exception as e:
                    logger.warning("Failed to fetch job details from %s: %s", url, e)
                    description = ""
                    location = "Remote"
                    posted_at = None

                external_id = self.make_external_id(self.name, url, title_text)
                jobs.append(
                    RawJob(
                        external_id=external_id,
                        source=self.name,
                        title=title_text,
                        company=company,
                        url=url,
                        description=description,
                        location=location,
                        posted_at=posted_at,
                    )
                )
            except Exception as e:
                logger.warning("Failed to parse job card: %s", e)
                continue

        return jobs
