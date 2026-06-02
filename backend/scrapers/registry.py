"""Scraper registry - add new sources here."""

import logging
from typing import Dict, List, Type

from scrapers.base import BaseScraper
from scrapers.arbeitnow import ArbeitnowScraper
from scrapers.remotive import RemotiveScraper
from scrapers.remoteok import RemoteOKScraper
from scrapers.rss_scraper import (
    HimalayasScraper,
    JobspressoScraper,
    WeWorkRemotelyScraper,
    WorkingNomadsScraper,
    CryptoJobsScraper,
    EuroperemotelyScraper,
    RemoteCoUkScraper,
    SkipTheDriveScraper,
    RemoteIndexScraper,
    RemotelyScraper,
    Remote4MeScraper,
    FourDayWeekScraper,
    RemotersScraper,
    LandingJobsScraper,
    RealWorkFromAnywhereScraper,
    RelocateMeScraper,
    CraigslistRemoteScraper,
    EuropeRemoteComScraper,
    HireWeb3Scraper,
)
from scrapers.greenhouse import GreenhouseScraper
from scrapers.devto import DevToScraper
from scrapers.nofluffjobs import NoFluffJobsScraper
from scrapers.virtualvocations import VirtualVocationsScraper
from scrapers.jobscollider import JobsColliderScraper
from scrapers.remotepython import RemotePythonScraper
from scrapers.fossjobs import FOSSJobsScraper
from scrapers.remoteworkhub import RemoteWorkHubScraper
from scrapers.ycombinator import YCombinatorScraper
from scrapers.justremote import JustRemoteScraper
from scrapers.linkedin import LinkedInScraper
from scrapers.himalayas_api import HimalayasAPIScraper
from scrapers.remotejobs_org import RemoteJobsOrgScraper
from scrapers.careernest import CareerNestScraper
from scrapers.talent import TalentScraper
from scrapers.rise import RiseScraper
from scrapers.ashby import AshbyScraper
from scrapers.themuse import MuseScraper
from scrapers.jobicy_api import JobicyAPIScraper
from scrapers.jobspy_scraper import JobSpyScraper
from scrapers.hn_algolia import HNAlgoliaScraper
from scrapers.remotefirstjobs import RemoteFirstJobsScraper
from scrapers.remoteyeah import RemoteYeahScraper
from scrapers.workable import WorkableScraper
from scrapers.lever import LeverScraper
from scrapers.smartrecruiters import SmartRecruitersScraper
from scrapers.adzuna import AdzunaScraper
from scrapers.recruitee import RecruiteeScraper
from scrapers.teamtailor import TeamTailorScraper
from scrapers.joincom import JoinComScraper
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
    "jobicy": JobicyAPIScraper,                     # ✅ API ★★★ - Jobicy API v2, 50 jobs/run
    "jobspresso": JobspressoScraper,                # 📡 RSS ★★☆ - RSS feed
    "fossjobs": FOSSJobsScraper,                    # 📡 RSS ★★☆ - RSS feed
    "jobscollider": JobsColliderScraper,            # 📡 RSS ★★☆ - RSS feed
    "remotepython": RemotePythonScraper,            # 📡 RSS ★★☆ - RSS feed
    "virtualvocations": VirtualVocationsScraper,    # 📡 RSS ★★☆ - RSS feed
    "remoteworkhub": RemoteWorkHubScraper,          # 📡 RSS ★★☆ - RSS feed
    "nofluffjobs": NoFluffJobsScraper,              # 📡 RSS ★★☆ - RSS feed
    "4dayweek": FourDayWeekScraper,                 # 📡 RSS ★★☆ - 4-day week jobs
    "remoters": RemotersScraper,                    # 📡 RSS ★★☆ - Remote jobs board
    "justremote": JustRemoteScraper,                # 📡 RSS ★★☆ - RSS feed
    # "ycombinator": YCombinatorScraper,            # 🌐 Web ★☆☆ - HTML parsing (fragile, requires auth, 0 jobs on Render)
    "linkedin": LinkedInScraper,                    # 🌐 Web ★★☆ - Uses LinkedIn guest API; 0 jobs without LINKEDIN_EMAIL/PASSWORD on Render

    # === New scrapers added June 2026 ===
    "himalayas_api": HimalayasAPIScraper,           # ✅ API ★★★ - 107K+ remote jobs, structured data
    "remotejobs_org": RemoteJobsOrgScraper,          # ✅ API ★★★ - 10K+ remote jobs from 5 sources
    "careernest": CareerNestScraper,                # ✅ API ★★★ - 9K+ global jobs, no auth
    "landingjobs": LandingJobsScraper,              # 📡 RSS ★★☆ - Tech-focused remote jobs club
    # "talent": TalentScraper,                      # 🌐 Web ★★☆ - HTML scraping (fragile, often 0 jobs on Render)
    "realworkfromanywhere": RealWorkFromAnywhereScraper, # 📡 RSS ★★☆ - Remote jobs board, 119 entries
    "rise": RiseScraper,                            # ✅ API ★★☆ - Jobs with salary, seniority data
    "ashby": AshbyScraper,                          # ✅ API ★★★ - Ashby ATS public API, 60+ companies
    "themuse": MuseScraper,                         # ✅ API ★★★ - The Muse public API, 8K+ remote jobs
    "jobspy": JobSpyScraper,                        # 🎭 Playwright ★★☆ - LinkedIn, Indeed, Glassdoor, Google, ZipRecruiter
    "hn_algolia": HNAlgoliaScraper,                 # ✅ API ★★★ - HN Who's Hiring via Algolia API
    "smartrecruiters": SmartRecruitersScraper,       # ✅ API ★★★ - SmartRecruiters ATS public API
    "adzuna": AdzunaScraper,                        # ✅ API ★★☆ - Adzuna aggregator (free API key required)
    "europeremotecom": EuropeRemoteComScraper,      # 📡 RSS ★★☆ - European remote jobs
    "hireweb3": HireWeb3Scraper,                    # 📡 RSS ★★☆ - Web3 remote jobs
    "remotefirstjobs": RemoteFirstJobsScraper,      # 📡 RSS ★★☆ - RemoteFirstJobs, 100+ jobs/feed
    "remoteyeah": RemoteYeahScraper,                # 📡 RSS ★★☆ - RemoteYeah, 260+ engineering jobs/feed

    # === Confirmed broken scrapers (tested, return 0 jobs) ===
    # "indeed": IndeedScraper,                       # Returns 403 block page from Indeed
    # "wellfound": WellfoundScraper,                 # API blocked, Playwright not installed
    # "angellist": AngelListScraper,                 # Delegates to Wellfound (same block)
    # "remoteco": RemoteCoScraper,                   # Cloudflare timeout
    # "google_jobs": GoogleJobsScraper,              # Returns 0 jobs (Google anti-scraping)
    # "naukri": NaukriScraper,                       # Auth required, no credentials
    # "instahyre": InstahyreScraper,                 # Auth required, login wall
    # "glassdoor": GlassdoorScraper,                 # Auth required, login wall
    # "unstop": UnstopScraper,                       # Auth required, wrong audience (internships)
    # "twitter_jobs": TwitterJobsScraper,            # X.com blocks all scraping
    # "github_jobs": GitHubJobsScraper,              # GitHub Issues hack, returns 0 jobs
    # "stackoverflow": StackOverflowScraper,         # SO Jobs shut down 2022
    # "weworkremotely_advanced": WeWorkRemotelyAdvancedScraper,  # Duplicate of weworkremotely
    # "workable": WorkableScraper,                   # All 55 companies return 302 → /oops pages; 0 jobs
    # "lever": LeverScraper,                         # All 30 companies return 401 (Lever API now requires auth)
    # "recruitee": RecruiteeScraper,                 # All 10 company slugs return 404 (dead)
    # "teamtailor": TeamTailorScraper,               # All 10 company slugs return 404 (dead)
    # "joincom": JoinComScraper,                     # All 10 company slugs return 404 (dead)
    # "relocateme": RelocateMeScraper,               # RSS feed returns 404
    # "craigslist": CraigslistRemoteScraper,         # RSS feed returns 404
    # "workingnomads": WorkingNomadsScraper,         # RSS returns 403 auth wall
    # "cryptojobs": CryptoJobsScraper,               # RSS feed returns 404
    # "europeremotely": EuroperemotelyScraper,       # RSS feed returns 403
    # "remotecouk": RemoteCoUkScraper,               # DNS error (remote.co.uk down)
    # "skipthedrive": SkipTheDriveScraper,           # RSS returns 302 redirect, no valid content
    # "remoteindex": RemoteIndexScraper,             # RSS feed returns 404
    # "remotely": RemotelyScraper,                   # RSS feed returns 404
    # "remote4me": Remote4MeScraper,                 # RSS feed returns 404
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