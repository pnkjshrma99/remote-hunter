"""Scraper registry - add new sources here."""

import logging
from typing import Dict, List, Type

from scrapers.base import BaseScraper
from scrapers.arbeitnow import ArbeitnowScraper
from scrapers.remotive import RemotiveScraper
from scrapers.remoteok import RemoteOKScraper
from scrapers.rss_scraper import (
    HimalayasScraper,
    JobicyScraper,
    JobspressoScraper,
    WeWorkRemotelyScraper,
    WorkingNomadsScraper,
)
from scrapers.greenhouse import GreenhouseScraper
from scrapers.linkedin import LinkedInScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

SCRAPER_REGISTRY: Dict[str, Type[BaseScraper]] = {
    "remotive": RemotiveScraper,
    "remoteok": RemoteOKScraper,
    "weworkremotely": WeWorkRemotelyScraper,
    "workingnomads": WorkingNomadsScraper,
    "himalayas": HimalayasScraper,
    "jobicy": JobicyScraper,
    "jobspresso": JobspressoScraper,
    "greenhouse": GreenhouseScraper,
    "linkedin": LinkedInScraper,
    "arbeitnow": ArbeitnowScraper,
}


def get_all_scrapers(source_names: list[str] | None = None) -> List[BaseScraper]:
    if not source_names:
        return [cls() for cls in SCRAPER_REGISTRY.values()]
    selected = []
    for name in source_names:
        scraper = SCRAPER_REGISTRY.get(name)
        if scraper:
            selected.append(scraper())
    return selected


def run_all_scrapers(
    strict_junior: bool = False,
    criteria: SearchCriteria | None = None,
    source_names: list[str] | None = None,
) -> List[RawJob]:
    all_jobs: List[RawJob] = []
    seen_ids = set()
    for scraper in get_all_scrapers(source_names=source_names):
        for job in scraper.run(strict_junior=strict_junior, criteria=criteria):
            if job.external_id not in seen_ids:
                seen_ids.add(job.external_id)
                all_jobs.append(job)
    logger.info("Total unique jobs from all scrapers: %d", len(all_jobs))
    return all_jobs
