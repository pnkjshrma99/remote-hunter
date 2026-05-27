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
from scrapers.remoteco import RemoteCoScraper
from scrapers.angellist import AngelListScraper
from scrapers.weworkremotely_advanced import WeWorkRemotelyAdvancedScraper
from scrapers.justremote import JustRemoteScraper
from scrapers.nofluffjobs import NoFluffJobsScraper
from scrapers.wellfound import WellfoundScraper
from scrapers.github_jobs import GitHubJobsScraper
from scrapers.devto import DevToScraper
from scrapers.ycombinator import YCombinatorScraper
from scrapers.virtualvocations import VirtualVocationsScraper
from scrapers.jobscollider import JobsColliderScraper
from scrapers.remotepython import RemotePythonScraper
from scrapers.fossjobs import FOSSJobsScraper
from scrapers.remoteworkhub import RemoteWorkHubScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

# FIXED: Updated registry with working sources enabled
# Enabled: sources verified working from feed tests
# Disabled: sources known to be dead, blocked, or requiring auth
SCRAPER_REGISTRY: Dict[str, Type[BaseScraper]] = {
    "remotive": RemotiveScraper,
    "remoteok": RemoteOKScraper,
    "arbeitnow": ArbeitnowScraper,
    "greenhouse": GreenhouseScraper,
    "linkedin": LinkedInScraper,
    "weworkremotely": WeWorkRemotelyScraper,
    "weworkremotely_advanced": WeWorkRemotelyAdvancedScraper,
    "devto": DevToScraper,
    "himalayas": HimalayasScraper,
    "jobicy": JobicyScraper,
    "jobspresso": JobspressoScraper,
    "fossjobs": FOSSJobsScraper,
    "jobscollider": JobsColliderScraper,
    "remotepython": RemotePythonScraper,
    "virtualvocations": VirtualVocationsScraper,
    "remoteworkhub": RemoteWorkHubScraper,
    # Disabled sources due to blocking/rate limiting/dead URLs
    # "nofluffjobs": NoFluffJobsScraper,  # DISABLED: HTTP 429 rate limiting
    # "justremote": JustRemoteScraper,  # DISABLED: Returns 0 jobs consistently
    # "workingnomads": WorkingNomadsScraper,  # DISABLED: HTTP 404 dead URL
    # "remoteco": RemoteCoScraper,  # DISABLED: Timeout errors
    # "angellist": AngelListScraper,  # DISABLED: HTTP 403 blocked
    # "wellfound": WellfoundScraper,  # DISABLED: HTTP 403 blocked
    # "github_jobs": GitHubJobsScraper,  # DISABLED: HTTP 403 rate limit exceeded
    # "stackoverflow": StackOverflowScraper,  # DISABLED: StackOverflow Jobs shut down in 2022
    # "ycombinator": YCombinatorScraper,  # DISABLED: API returns 404, fallback ineffective
}


def get_all_scrapers(source_names: list[str] | None = None) -> List[BaseScraper]:
    if not source_names:
        return [cls() for cls in SCRAPER_REGISTRY.values()]
    selected = []
    for name in source_names:
        scraper = SCRAPER_REGISTRY.get(name)
        if scraper:
            selected.append(scraper())
        else:
            logger.warning("Scraper '%s' not found in registry", name)
    return selected


def run_all_scrapers(
    strict_junior: bool = False,
    criteria: SearchCriteria | None = None,
    source_names: list[str] | None = None,
) -> List[RawJob]:
    all_jobs: List[RawJob] = []
    seen_ids = set()
    for scraper in get_all_scrapers(source_names=source_names):
        try:
            for job in scraper.run(strict_junior=strict_junior, criteria=criteria):
                if job.external_id not in seen_ids:
                    seen_ids.add(job.external_id)
                    all_jobs.append(job)
        except Exception as e:
            logger.error("Scraper %s failed: %s", scraper.name, e)
    logger.info("Total unique jobs from all scrapers: %d", len(all_jobs))
    return all_jobs