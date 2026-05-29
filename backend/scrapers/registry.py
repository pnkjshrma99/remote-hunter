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
from scrapers.stackoverflow import StackOverflowScraper
from scrapers.devto import DevToScraper
from scrapers.ycombinator import YCombinatorScraper
from scrapers.virtualvocations import VirtualVocationsScraper
from scrapers.jobscollider import JobsColliderScraper
from scrapers.remotepython import RemotePythonScraper
from scrapers.fossjobs import FOSSJobsScraper
from scrapers.remoteworkhub import RemoteWorkHubScraper
from scrapers.naukri import NaukriScraper
from scrapers.instahyre import InstahyreScraper
from scrapers.glassdoor import GlassdoorScraper
from scrapers.unstop import UnstopScraper
from scrapers.twitter_jobs import TwitterJobsScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

# Scraper Registry
# ================
# Each entry maps a source name to its scraper class.
#
# Source classifications:
#   ✅ API      - Public API, no auth required (most reliable)
#   📡 RSS      - RSS/Atom feed (reliable, less structured)
#   🌐 Web      - HTML scraping (brittle, may break on site changes)
#   🔒 Auth     - Requires login/cookies/API key (may fail silently)
#   💀 Dead     - Source no longer available
#
# Reliability legend:
#   ★★★ - Very reliable (dedicated API)
#   ★★☆ - Moderately reliable (RSS/structured)
#   ★☆☆ - Unreliable (HTML scraping, auth-gated)
#   ☆☆☆ - Dead/moved

SCRAPER_REGISTRY: Dict[str, Type[BaseScraper]] = {
    # === API-based scrapers (most reliable) ===
    "remotive": RemotiveScraper,            # ✅ API ★★★ - Public API, no auth
    "remoteok": RemoteOKScraper,            # ✅ API ★★★ - Public API, no auth
    "arbeitnow": ArbeitnowScraper,          # ✅ API ★★★ - Public API, no auth
    "devto": DevToScraper,                  # ✅ API ★★★ - Public API, no auth
    "greenhouse": GreenhouseScraper,        # ✅ API ★★★ - Public ATS board API

    # === RSS-based scrapers (reliable) ===
    "weworkremotely": WeWorkRemotelyScraper,       # 📡 RSS ★★☆ - RSS feed
    "weworkremotely_advanced": WeWorkRemotelyAdvancedScraper,  # 📡 RSS ★★☆
    "himalayas": HimalayasScraper,                  # 📡 RSS ★★☆ - RSS feed
    "jobicy": JobicyScraper,                        # 📡 RSS ★★☆ - RSS feed
    "jobspresso": JobspressoScraper,                # 📡 RSS ★★☆ - RSS feed
    "fossjobs": FOSSJobsScraper,                    # 📡 RSS ★★☆ - RSS feed
    "jobscollider": JobsColliderScraper,            # 📡 RSS ★★☆ - RSS feed
    "remotepython": RemotePythonScraper,            # 📡 RSS ★★☆ - RSS feed
    "virtualvocations": VirtualVocationsScraper,    # 📡 RSS ★★☆ - RSS feed
    "remoteworkhub": RemoteWorkHubScraper,          # 📡 RSS ★★☆ - RSS feed
    "nofluffjobs": NoFluffJobsScraper,              # 📡 RSS ★★☆ - RSS feed
    "justremote": JustRemoteScraper,                # 📡 RSS ★★☆ - RSS feed
    "workingnomads": WorkingNomadsScraper,          # 📡 RSS ★★☆ - RSS feed

    # === Web-scraping scrapers (less reliable, may break) ===
    "ycombinator": YCombinatorScraper,      # 🌐 Web ★★☆ - API + HTML fallback
    "linkedin": LinkedInScraper,            # 🌐 Web ★☆☆ - HTML scraping (brittle, often blocked)
    "remoteco": RemoteCoScraper,            # 🌐 Web ★☆☆ - Uses Playwright/Cloudflare bypass
    "angellist": AngelListScraper,          # 🌐 Web ★☆☆ - Delegates to Wellfound
    "wellfound": WellfoundScraper,          # 🌐 Web ★☆☆ - Playwright + JSON API
    "github_jobs": GitHubJobsScraper,       # 🌐 Web ★☆☆ - Uses Issues API (hack)

    # === Auth-gated scrapers (may fail with auth wall) ===
    "naukri": NaukriScraper,               # 🔒 Auth ★☆☆ - API blocks without cookies
    "instahyre": InstahyreScraper,         # 🔒 Auth ★☆☆ - Requires login
    "glassdoor": GlassdoorScraper,         # 🔒 Auth ★☆☆ - Blocks scrapers aggressively
    "unstop": UnstopScraper,               # 🔒 Auth ★☆☆ - Requires login
    "twitter_jobs": TwitterJobsScraper,    # 🔒 Auth ★☆☆ - X.com requires auth

    # === Dead/moved scrapers ===
    "stackoverflow": StackOverflowScraper,  # 💀 Dead ☆☆☆ - SO Jobs shut down 2022
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