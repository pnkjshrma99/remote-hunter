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
    CryptoJobsScraper,
    EuroperemotelyScraper,
    RemoteCoUkScraper,
    SkipTheDriveScraper,
)
from scrapers.greenhouse import GreenhouseScraper
from scrapers.devto import DevToScraper
from scrapers.nofluffjobs import NoFluffJobsScraper
from scrapers.virtualvocations import VirtualVocationsScraper
from scrapers.jobscollider import JobsColliderScraper
from scrapers.remotepython import RemotePythonScraper
from scrapers.fossjobs import FOSSJobsScraper
from scrapers.remoteworkhub import RemoteWorkHubScraper
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
    "himalayas": HimalayasScraper,                  # 📡 RSS ★★☆ - RSS feed
    "jobicy": JobicyScraper,                        # 📡 RSS ★★☆ - RSS feed
    "jobspresso": JobspressoScraper,                # 📡 RSS ★★☆ - RSS feed
    "fossjobs": FOSSJobsScraper,                    # 📡 RSS ★★☆ - RSS feed
    "jobscollider": JobsColliderScraper,            # 📡 RSS ★★☆ - RSS feed
    "remotepython": RemotePythonScraper,            # 📡 RSS ★★☆ - RSS feed
    "virtualvocations": VirtualVocationsScraper,    # 📡 RSS ★★☆ - RSS feed
    "remoteworkhub": RemoteWorkHubScraper,          # 📡 RSS ★★☆ - RSS feed
    "nofluffjobs": NoFluffJobsScraper,              # 📡 RSS ★★☆ - RSS feed
    "workingnomads": WorkingNomadsScraper,          # 📡 RSS ★★☆ - RSS feed
    "cryptojobs": CryptoJobsScraper,                # 📡 RSS ★★☆ - Web3/blockchain
    "europeremotely": EuroperemotelyScraper,        # 📡 RSS ★★☆ - European remote
    "remotecouk": RemoteCoUkScraper,                # 📡 RSS ★★☆ - UK remote jobs
    "skipthedrive": SkipTheDriveScraper,            # 📡 RSS ★★☆ - Remote aggregator
}

# Disabled scrapers (kept for reference, may be re-enabled with fixes):
# "ycombinator": YCombinatorScraper,                 # 🌐 Web - Regex-based, fragile, no descriptions
# "linkedin": LinkedInScraper,                       # 🌐 Web - Guest API blocked, auth is fragile
# "remoteco": RemoteCoScraper,                       # 🌐 Web - Cloudflare protected
# "wellfound": WellfoundScraper,                     # 🌐 Web - Blocked, occasional Playwright success
# "angellist": AngelListScraper,                     # 🌐 Web - Delegates to Wellfound (same block)
# "indeed": IndeedScraper,                           # 🌐 Web - Indeed blocks aggressively
# "google_jobs": GoogleJobsScraper,                  # 🌐 Web - Google blocks automated requests
# "justremote": JustRemoteScraper,                   # 📡 RSS - RSS feed unreliable, search URL broken
# "naukri": NaukriScraper,                           # 🔒 Auth - API obfuscated, no descriptions
# "instahyre": InstahyreScraper,                     # 🔒 Auth - Requires login, selectors wrong
# "glassdoor": GlassdoorScraper,                     # 🔒 Auth - Blocks scrapers aggressively
# "unstop": UnstopScraper,                           # 🔒 Auth - Internships, not remote jobs
# "twitter_jobs": TwitterJobsScraper,                # 🔒 Auth - X.com blocks all scraping
# "github_jobs": GitHubJobsScraper,                  # 🌐 Web - GitHub Issues hack, never returns jobs
# "stackoverflow": StackOverflowScraper,             # 💀 Dead - SO Jobs shut down 2022
# "weworkremotely_advanced": WeWorkRemotelyAdvancedScraper,  # 📡 RSS - Duplicate of weworkremotely


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