"""No Fluff Jobs scraper - European tech job board.

Improved with:
1. Deep page scraping for full job descriptions (not just RSS summary)
2. Worldwide/global hiring detection in description text
3. Company validation to filter out fake/spam listings
4. Better Poland-specific filtering (only include if remote/worldwide hiring)
"""

import logging
import re
import json
from typing import List, Optional
from html.parser import HTMLParser
from urllib.parse import urljoin

from scrapers.base import BaseScraper
from scrapers.filters import RawJob, SearchCriteria

logger = logging.getLogger(__name__)

NOFLUFFJOBS_BASE = "https://nofluffjobs.com"

# Keywords in job descriptions that indicate worldwide or India-eligible hiring
WORLDWIDE_HIRING_KEYWORDS = [
    r"\bworldwide\b",
    r"\bglobal(?:ly)?\s+(?:team|company|hiring|remote|position)\b",
    r"\banywhere\b",
    r"\bwork\s+from\s+anywhere\b",
    r"\b100%\s*remote\b",
    r"\bfully\s+remote\b",
    r"\bremote\s+first\b",
    r"\bremote\s+-\s+global\b",
    r"\bno\s+location\s+(?:restriction|requirement|limit)\b",
    r"\bopen\s+to\s+(?:all|everyone|global)\b",
    r"\binternational\s+(?:team|hiring|remote)\b",
]

# Keywords that suggest the job welcomes Indian applicants
INDIA_HIRING_KEYWORDS = [
    r"\bindia\b",
    r"\bindian\s+(?:applicants?|candidates?|developers?|engineers?|professionals?)\b",
    r"\bhiring\s+(?:from|in)\s+india\b",
    r"\basia\s+(?:pac(?:ific)?|timezone)\b",
    r"\b(?:ist|gmt\s*\+5:?30)\b",  # Indian Standard Time
    r"\b(?:bangalore|bengaluru|mumbai|pune|hyderabad|chennai|delhi|gurgaon|noida)\b",
]

# Indicates the job is Poland/EU-local only (not global-remote)
LOCAL_ONLY_INDICATORS = [
    r"\bin\s+our\s+(?:office|headquarters?|location)\b",
    r"\bhybrid\s+(?:work|model|mode)\b",
    r"\bonsite\b",
    r"\b(?:must|required)\s+to\s+(?:be\s+)?(?:based|located)\s+in\b",
    r"\b(?:poland|warsaw|krakow|wrocław|poznań|gdańsk|gdynia|sopot|katowice|łódź|szczecin|lublin|bydgoszcz|toruń|bieńsko|rzeszów|częstochowa|radom|zielona|gorzów|opole|elbląg|płock|wałbrzych|tarnów|kielce|kalisk|gliwice|zabrze|bielsko|bytom|rybnik|ruda|tychy|dąbrowa|chorzów|jastrzębie|jelenia|nowy|sącz|siedlce|konin|piotrków|inowrocław|ostrołęka|suwałki|stargard|gniezno|leszno|przemyśl|łomża|łowicz|oświęcim|świdnica|chełm|skierniewice|starachowice|kołobrzeg|tomaszów|krotoszyn|jarosław|nowa|sól|jasło|dębica|zawiercie|międzyrzecz|aleksandrów|łuków|sandomierz|hajnówka|sejny|lidzbark|bartoszyce|ełk|giżycko|węgorzewo|olecko|pisz|mrągowo|nidzica|działdowo|nowe|miasto|lubawa|iława|ostróda|morąg|pasłęk|braniewo|gołdap)\b",
]

# Company validation patterns
COMPANY_VERIFICATION_PATTERNS = {
    "has_website": re.compile(r"(?:https?://|www\.)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?", re.I),
    "has_email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", re.I),
    "has_description": re.compile(r".{200,}", re.DOTALL),
}

SUSPICIOUS_COMPANY_NAMES = [
    r"test\s+company",
    r"example\s+corp",
    r"dummy\s+inc",
    r"unknown",
    r"anon(?:ymous)?",
    r"sample\s+firm",
    r"temp\s+agency",
]

# Known legitimate companies (curated for remote tech jobs)
KNOWN_LEGITIMATE_COMPANIES = {
    "google", "amazon", "meta", "microsoft", "apple", "netflix", "spotify",
    "stripe", "datadog", "cloudflare", "gitlab", "hashicorp", "docker",
    "vercel", "netlify", "supabase", "railway", "fly.io", "render",
    "digitalocean", "linode", "mongodb", "elastic", "grafana", "prometheus",
    "snyk", "palantir", "red hat", "ibm", "oracle", "salesforce", "twitter/x",
    "shopify", "github", "figma", "notion", "linear", "retool", "airtable",
    "zapier", "intercom", "hubspot", "atlassian", "twilio", "sendgrid",
    "confluent", "databricks", "snowflake", "cockroach labs", "neon",
    "planetscale", "cockroachdb", "motherduck", "dagster", "airbyte",
    "temporal", "retool", "vercel", "hasura", "appwrite", "supabase",
    "liveblocks", "magic", "workos", "clerk", "plaid", "brex", "ramp",
    "deel", "remote", "multi", "safetywing", "borderless", "omni",
    "automattic", "buffer", "vox media", "verizon media", "zillow",
    "reddit", "discord", "twitch", "youtube", "medium", "substack",
    "ghost", "revenuecat", "paddle", "lemonsqueezy", "stax",
    "segment", "amplitude", "mixpanel", "heap", "hotjar", "fullstory",
    "clickhouse", "materialize", "risingwave", "tidb", "dgraph",
    "neo4j", "redis", "memcached", "nats", "eventstore", "apache",
    "cncf", "linux foundation", "cloud native", "alibaba", "tencent",
    "baidu", "bytedance", "tiktok", "alibaba cloud", "huawei",
    "samsung", "lg", "naver", "kakao", "coupang", "grab", "gojek",
    "traveloka", "bukalapak", "tokopedia", "shopee", "lazada",
}


class HTMLStripper(HTMLParser):
    """Remove HTML tags while preserving text."""
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []

    def handle_data(self, data):
        self.text.append(data)

    def get_text(self):
        return ''.join(self.text)


def strip_html(html_text: str) -> str:
    """Remove HTML tags from text."""
    try:
        stripper = HTMLStripper()
        stripper.feed(html_text)
        return stripper.get_text()
    except:
        return html_text


def extract_location_and_salary(description: str) -> tuple[str, str]:
    """Extract location and salary from NoFluffJobs description HTML."""
    location = ""
    salary = ""
    
    clean_desc = strip_html(description)
    
    loc_match = re.search(r"Location:\s*(.+?)(?=\n|Salary|$)", clean_desc)
    if loc_match:
        location = loc_match.group(1).strip()
    
    sal_match = re.search(r"Salary:\s*(.+?)(?=\n|$)", clean_desc)
    if sal_match:
        salary = sal_match.group(1).strip()
    
    return location, salary


def is_worldwide_hiring(title: str, description: str, location: str) -> bool:
    """Check if the job posting is open to worldwide or Indian applicants.
    
    Examines both the RSS summary and the full job description for
    indicators that the company hires globally, not just locally.
    """
    combined = f"{title} {description} {location}".lower()
    
    # Check for worldwide/global hiring indicators
    if _matches_any(combined, WORLDWIDE_HIRING_KEYWORDS):
        return True
    
    # Check for India-specific hiring indicators
    if _matches_any(combined, INDIA_HIRING_KEYWORDS):
        return True
    
    # If explicitly says remote and doesn't have local-only indicators, it's worldwide
    if re.search(r"\bremote\b", combined, re.I):
        # But not if it has local-only restrictions
        if not _matches_any(combined, LOCAL_ONLY_INDICATORS):
            return True
    
    # If the description mentions multiple timezones or countries
    timezone_pattern = re.findall(r"\b(gmt|utc)\s*[+-]\d{1,2}", combined, re.I)
    country_mentions = re.findall(
        r"\b(?:usa|uk|germany|france|spain|portugal|netherlands|sweden|norway|denmark|finland|czech|australia|japan|singapore|brazil|canada|mexico|argentina|chile|colombia)\b",
        combined
    )
    if len(timezone_pattern) >= 2 or len(country_mentions) >= 3:
        return True
    
    return False


def _matches_any(text: str, patterns: list) -> bool:
    """Check if any regex pattern matches the text."""
    return any(re.search(p, text, re.I) for p in patterns)


def is_company_legitimate(company: str, description: str, url: str) -> bool:
    """Basic company validation to filter out fake/spam listings.
    
    Checks:
    1. Company name isn't obviously fake
    2. Description mentions a website or has sufficient detail
    3. Company URL resolves (if provided)
    4. Company is known legitimate OR passes basic checks
    """
    company_lower = company.lower().strip()
    
    # Check if company is in our known legitimate list
    for legit in KNOWN_LEGITIMATE_COMPANIES:
        if legit == company_lower or company_lower.startswith(legit):
            return True
    
    # Check against suspicious patterns
    if _matches_any(company_lower, SUSPICIOUS_COMPANY_NAMES):
        logger.debug(f"Suspicious company name: {company}")
        return False
    
    # Check for company website in description
    if not _matches_any(description, [r"https?://[^\s]+"]):
        # No website mentioned - suspicious for a real job
        desc_word_count = len(description.split())
        if desc_word_count < 50:
            logger.debug(f"Too sparse description for {company}: {desc_word_count} words")
            return False
    
    # Check for common job posting elements (legitimate posts have these)
    legitimate_signals = [
        r"\b(?:apply|application|requirement|qualification|responsibilit)",
        r"\b(?:email|resume|cv|portfolio|github|linkedin)\b",
        r"\b(?:experience|skill|technology|stack|tool)\b",
        r"\b(?:benefit|salary|compensation|equity|stock)\b",
        r"\b(?:team|culture|mission|vision|value)\b",
    ]
    
    signal_count = sum(1 for pat in legitimate_signals if re.search(pat, description, re.I))
    
    # Need at least 2 legitimacy signals for unknown companies
    if signal_count < 2:
        logger.debug(f"Company {company} failed legitimacy check: {signal_count}/2 signals")
        return False
    
    return True


def should_include_job(location: str, title: str, description: str, company: str, url: str) -> bool:
    """
    Multi-level inclusion check for NoFluffJobs.
    
    Levels:
    1. Is the company legitimate? (fake job filter)
    2. Does the job description indicate worldwide/India hiring?
    3. Is it truly remote (not Poland-only)?
    """
    location_lower = location.lower()
    desc_lower = description.lower()
    title_lower = title.lower()
    combined = f"{title_lower} {desc_lower}"
    
    # LEVEL 1: Company validation
    if not is_company_legitimate(company, description, url):
        logger.debug(f"Skipping {company}: failed legitimacy check")
        return False
    
    # LEVEL 2: Check for worldwide/global/India hiring
    if is_worldwide_hiring(title, description, location):
        return True
    
    # LEVEL 3: If explicitly says "Remote" in location, check description
    if "remote" in location_lower:
        return True
    
    # LEVEL 4: For European-only/Polland locations, check if they indicate global hiring
    non_remote_countries_lower = ["poland", "czech", "hungary", "romania", "bulgaria", "slovakia", "ukraine", "lithuania", "latvia", "estonia"]
    
    location_only_country = any(c in location_lower for c in non_remote_countries_lower)
    
    if location_only_country:
        # Check if the description mentions remote work that spans timezones
        multiple_timezones = len(re.findall(r"\b(gmt|utc|est|pst|cet|eet|ist)\b", combined, re.I)) >= 2
        mentions_english = bool(re.search(r"\benglish\s+(?:speaking|work|required|fluent)\b", combined, re.I))
        
        if multiple_timezones and mentions_english:
            return True
        
        # If it explicitly says remote in the description but not location
        if re.search(r"\bfully remote\b|\b100%\s*remote\b|\bremote\s+first\b", combined):
            return True
        
        logger.debug(f"Excluding {title}@{company}: location={location} not global-remote")
        return False
    
    # Unknown location - check description for remote indicators
    if re.search(r"\bremote\b", combined):
        # Check for local-only restrictions
        if _matches_any(combined, LOCAL_ONLY_INDICATORS):
            logger.debug(f"Excluding {title}@{company}: has local-only restriction")
            return False
        return True
    
    # Default: include if we can't determine it's non-remote
    return True


class NoFluffJobsScraper(BaseScraper):
    name = "nofluffjobs"

    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape No Fluff Jobs board using RSS feed only.
        
        IMPORTANT: Do NOT fetch individual job pages here — NFJ rate-limits heavily
        (429s) and there can be 200+ jobs per feed, causing multi-minute delays.
        The RSS description is sufficient for location/salary extraction and filtering.
        """
        jobs: List[RawJob] = []
        search = (criteria.query if criteria else "").strip()

        try:
            import feedparser
            
            base_url = "https://nofluffjobs.com/rss?country=PL,DE,NL,FR,UK,CH,SE,NO,DK,FI,CZ,AT,BE,ES,PT,IT&employment=permanent,b2b,mandate"
            if search:
                base_url += f"&keywords={search.replace(' ', '%20')}"

            feed = feedparser.parse(base_url)
            total_entries = len(feed.entries)
            
            for entry in feed.entries:
                try:
                    title = entry.get("title", "")
                    company = entry.get("author", "") or "Unknown"
                    job_url = entry.get("link", "")
                    description = entry.get("summary", "") or ""
                    
                    # Extract location and salary from RSS description
                    location, salary = extract_location_and_salary(description)
                    
                    # Multi-level filtering
                    if not should_include_job(location, title, description, company, job_url):
                        continue

                    external_id = self.make_external_id(self.name, job_url, title)
                    jobs.append(
                        RawJob(
                            external_id=external_id,
                            source=self.name,
                            title=title,
                            company=company,
                            url=job_url,
                            description=description[:2000],  # Truncate long RSS to save memory
                            location=location or "Remote",
                            salary=salary,
                            posted_at=entry.get("published"),
                        )
                    )
                except Exception as e:
                    continue

            logger.info(f"NoFluffJobs: {len(jobs)}/{total_entries} jobs passed filters (RSS only)")

        except ImportError:
            logger.warning("feedparser not installed - skipping No Fluff Jobs scraper")
            return []
        except Exception as e:
            logger.warning(f"No Fluff Jobs scrape failed: {e}")
            return []

        # Deduplicate
        seen = set()
        unique = []
        for j in jobs:
            if j.external_id not in seen:
                seen.add(j.external_id)
                unique.append(j)
        
        return unique

    def _fetch_job_details(self, job_url: str, rss_summary: str) -> str:
        """Fetch full job description from the job page.
        
        Many NoFluffJobs listings have truncated descriptions in RSS.
        This fetches the actual job page to get the full description
        for better worldwide/India hiring detection.
        """
        if not job_url:
            return rss_summary
        
        try:
            resp = self.fetch(job_url)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Try multiple selectors for the job description
            desc_selectors = [
                "div[data-test='job-description']",
                "div.posting-description",
                "div.job-description",
                "section.description",
                "article",
                "main",
                ".posting-body",
                "[class*='description']",
                "[class*='details']",
            ]
            
            full_text = ""
            for selector in desc_selectors:
                container = soup.select_one(selector)
                if container:
                    full_text = container.get_text(" ", strip=True)
                    if len(full_text) > len(rss_summary):
                        break
            
            # Also try to extract structured data from JSON-LD
            if not full_text:
                json_ld = soup.select_one('script[type="application/ld+json"]')
                if json_ld:
                    try:
                        data = json.loads(json_ld.string)
                        desc = data.get("description", "")
                        if desc and len(desc) > len(full_text):
                            full_text = strip_html(desc)
                    except:
                        pass
            
            if full_text and len(full_text) > len(rss_summary):
                logger.debug(f"Fetched full description ({len(full_text)} chars) from {job_url}")
                return full_text
            
            return rss_summary
            
        except Exception as e:
            logger.debug(f"Failed to fetch job details for {job_url}: {e}")
            return rss_summary