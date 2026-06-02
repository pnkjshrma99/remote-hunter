"""Smart filtering for runtime job searches."""

import re
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Set, Dict
import langdetect

logger = logging.getLogger(__name__)

# Role niches we care about - expanded to cover more categories
# Multi-level role taxonomy for semantic matching
# Maps each role category to the keywords/titles that belong to it.
# When a user searches for "DevOps Engineer", we can find all related roles.
ROLE_CATEGORIES = {
    "devops": {
        "keywords": [
            "devops engineer", "sre engineer", "site reliability engineer",
            "platform engineer", "infrastructure engineer", "cloud engineer",
            "reliability engineer", "cloud architect", "devsecops engineer",
            "devops", "sre", "site reliability",
            "dev ops engineer", "systems engineer", "systems administrator",
            "platform ops", "cloud ops",
            "dev secops", "devops lead",
        ],
    },
    "backend": {
        "keywords": [
            "backend engineer", "backend developer",
            "back-end engineer", "back-end developer",
            "back end engineer", "back end developer",
            "server engineer", "server developer",
            "api engineer", "api developer",
            "software engineer", "software developer",
            "backend", "back-end", "back end",
        ],
    },
    "frontend": {
        "keywords": [
            "frontend engineer", "frontend developer",
            "front-end engineer", "front-end developer",
            "front end engineer", "front end developer",
            "ui engineer", "ux engineer",
            "web developer", "web engineer",
            "frontend", "front-end", "front end",
        ],
    },
    "fullstack": {
        "keywords": [
            "full stack engineer", "fullstack engineer",
            "full-stack engineer",
            "full stack developer", "fullstack developer",
            "full stack", "fullstack", "full-stack",
        ],
    },
    "data": {
        "keywords": [
            "data scientist", "data engineer", "ml engineer",
            "machine learning engineer", "ai engineer",
            "artificial intelligence", "data analyst", "data science",
        ],
    },
    "mobile": {
        "keywords": [
            "mobile engineer", "mobile developer", "ios engineer",
            "android engineer", "android developer", "ios developer",
        ],
    },
    "qa": {
        "keywords": [
            "qa engineer", "quality assurance", "test engineer",
            "automation engineer", "qa", "test automation",
        ],
    },
    "security": {
        "keywords": [
            "security engineer", "devsecops", "cybersecurity",
            "security analyst", "security architect",
        ],
    },
}

# Flatten all keywords into a single list for backward-compatible role detection
ROLE_KEYWORDS = [
    rf"\b{re.escape(kw)}\b" for cat in ROLE_CATEGORIES.values() for kw in cat["keywords"]
]

# Shortcut: build compiled patterns for each role category
_ROLE_CATEGORY_PATTERNS: Dict[str, List[re.Pattern]] = {}
for category, data in ROLE_CATEGORIES.items():
    _ROLE_CATEGORY_PATTERNS[category] = [
        re.compile(rf"\b{re.escape(kw)}\b", re.I) for kw in data["keywords"]
    ]

JUNIOR_KEYWORDS = [
    r"\bjunior\b",
    r"\bentry[\s-]?level\b",
    r"\bassociate\b",
    r"\bgraduate\b",
    r"\bnew grad\b",
    r"\b0[\s-]?2\s*years?\b",
    r"\b1[\s-]?2\s*years?\b",
    r"\b0\s*year\b",
    r"\b1\s*year\b",
    r"\b2\s*years?\b",
    r"\bearly career\b",
    r"\bentry\b",
    r"\btrainee\b",
    r"\bapprentice\b",
    r"\bi\b",
    r"\bintern\b",
]

SENIOR_EXCLUDE = [
    r"\bsenior\b",
    r"\bsr\.?\b",
    r"\bstaff\b",
    r"\bprincipal\b",
    r"\blead\b",
    r"\bhead of\b",
    r"\bmanager\b",
    r"\bdirector\b",
    r"\bvp\b",
    r"\b5\+?\s*years?\b",
    r"\b6\+?\s*years?\b",
    r"\b7\+?\s*years?\b",
    r"\b8\+?\s*years?\b",
    r"\b10\+?\s*years?\b",
]

REMOTE_POSITIVE = [
    r"\bworldwide\b",
    r"\banywhere\b",
    r"\bglobal\b",
    r"\bremote anywhere\b",
    r"\bwork from anywhere\b",
    r"\bfully remote\b",
    r"\b100%\s*remote\b",
    r"\bremote\s*-\s*global\b",
    r"\binternational\b",
    r"\bno location restriction\b",
    r"\bopen to all\b",
    r"\bapac\b",
    r"\bemea\b",
    r"\bremote\b",
]

REMOTE_NEGATIVE = [
    r"\bhybrid\b",
    r"\bonsite\b",
    r"\bon-site\b",
    r"\bon site\b",
    r"\bin-office\b",
    r"\bin office\b",
    r"\bus only\b",
    r"\busa only\b",
    r"\bunited states only\b",
    r"\beu only\b",
    r"\beurope only\b",
    r"\buk only\b",
    r"\bcanada only\b",
    r"\bindia only\b",
    r"\bindia-only\b",
    r"\bmust be in\b",
    r"\blocal candidates\b",
    r"\bno remote\b",
]

INDIAN_HQ_COMPANIES = {
    "tcs", "tata consultancy", "infosys", "wipro", "hcl", "tech mahindra",
    "cognizant", "mindtree", "mphasis", "ltimindtree", "lti", "persistent",
    "zoho", "freshworks", "flipkart", "paytm", "ola", "swiggy", "zomato",
    "byju", "razorpay", "phonepe", "cred", "meesho", "inmobi", "mu sigma",
    "capgemini india", "accenture india", "genpact", "mphasis", "cyient",
    "hexaware", "birlasoft", "niit", "sonata", "mastek", "zensar",
}

# Indian cities that indicate a locally-bound job (not truly global-remote)
INDIAN_CITIES = {
    "gurgaon", "gurugram", "bangalore", "bengaluru", "mumbai", "pune",
    "hyderabad", "chennai", "noida", "delhi", "kolkata", "ahmedabad",
    "jaipur", "chandigarh", "indore", "kochi", "coimbatore", "thiruvananthapuram",
    "lucknow", "bhopal", "nagpur", "visakhapatnam", "vadodara", "surat",
    "mohali", "thane", "navi mumbai", "whitefield", "electronic city",
    "hitech city", "gachibowli", "madhapur", "kondapur", "marathahalli",
}

INDIAN_STATE_KEYWORDS = {
    "karnataka", "maharashtra", "tamil nadu", "telangana", "andhra pradesh",
    "kerala", "gujarat", "rajasthan", "uttar pradesh", "delhi ncr",
    "ncr", "haryana", "punjab", "west bengal", "madhya pradesh",
}

TECH_STACK_MAP = {
    "AWS": [r"\baws\b", r"\bamazon web services\b"],
    "GCP": [r"\bgcp\b", r"\bgoogle cloud\b"],
    "Azure": [r"\bazure\b", r"\bmicrosoft azure\b"],
    "Kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
    "Docker": [r"\bdocker\b", r"\bcontainers?\b"],
    "Terraform": [r"\bterraform\b", r"\biac\b", r"\binfrastructure as code\b"],
    "CI/CD": [r"\bci/?cd\b", r"\bjenkins\b", r"\bgithub actions\b", r"\bgitlab ci\b", r"\bargo\s*cd\b"],
    "Python": [r"\bpython\b"],
    "Go": [r"\bgolang\b", r"\bgo\b"],
    "Linux": [r"\blinux\b", r"\bunix\b"],
    "Ansible": [r"\bansible\b"],
    "Prometheus": [r"\bprometheus\b", r"\bgrafana\b", r"\bobservability\b"],
    "Helm": [r"\bhelm\b"],
    "Pulumi": [r"\bpulumi\b"],
    "CloudFormation": [r"\bcloudformation\b"],
    # Additional tech stacks
    "JavaScript": [r"\bjavascript\b", r"\bjs\b"],
    "TypeScript": [r"\btypescript\b", r"\bts\b"],
    "React": [r"\breact\b", r"\breactjs\b"],
    "Vue": [r"\bvue\b", r"\bvuejs\b"],
    "Angular": [r"\bangular\b"],
    "Node.js": [r"\bnode\.?js\b", r"\bnodejs\b"],
    "Java": [r"\bjava\b"],
    "Spring": [r"\bspring\b", r"\bspring boot\b"],
    "C#": [r"\bc#\b", r"\bcsharp\b"],
    ".NET": [r"\.net\b"],
    "PHP": [r"\bphp\b"],
    "Ruby": [r"\bruby\b", r"\brails\b"],
    "Swift": [r"\bswift\b"],
    "Kotlin": [r"\bkotlin\b"],
    "Rust": [r"\brust\b"],
    "SQL": [r"\bsql\b", r"\bpostgresql\b", r"\bmysql\b"],
    "MongoDB": [r"\bmongodb\b", r"\bmongo\b"],
    "Redis": [r"\bredis\b"],
    "GraphQL": [r"\bgraphql\b"],
    "REST": [r"\brest\b", r"\brestful\b"],
    "Git": [r"\bgit\b"],
    "Agile": [r"\bagile\b", r"\bscrum\b"],
    "DevOps": [r"\bdevops\b"],
    "Machine Learning": [r"\bml\b", r"\bmachine learning\b", r"\bai\b"],
    "Data Science": [r"\bdata science\b"],
    "Blockchain": [r"\bblockchain\b", r"\bweb3\b"],
    "Mobile": [r"\bmobile\b", r"\bios\b", r"\bandroid\b"],
    "Security": [r"\bsecurity\b", r"\bcybersecurity\b"],
}


@dataclass
class RawJob:
    external_id: str
    source: str
    title: str
    company: str
    url: str
    description: str = ""
    location: str = ""
    salary: str = ""
    posted_at: Optional[str] = None


@dataclass
class SearchCriteria:
    query: str = "DevOps Engineer"
    job_profile_id: Optional[str] = None
    min_experience: Optional[int] = None
    max_experience: Optional[int] = None
    posted_within_days: Optional[int] = 14
    remote_only: bool = True
    global_or_india: bool = True
    exclude_indian_hq: bool = True
    strict_experience: bool = False
    strict_title: bool = False
    linkedin_urls: Optional[List[str]] = None

    @property
    def query_terms(self) -> List[str]:
        terms = re.findall(r"[a-zA-Z0-9+#.]+", self.query.lower())
        stop_words = {"engineer", "developer", "remote", "job", "jobs", "role", "roles"}
        return [term for term in terms if term not in stop_words]


def _matches_any(text: str, patterns: List[str]) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    if value.isdigit():
        try:
            timestamp = int(value)
            if timestamp > 10_000_000_000:
                timestamp = timestamp // 1000
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(tzinfo=None)
        except (OSError, ValueError):
            return None
    cleaned = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(cleaned)
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        pass
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
        except ValueError:
            continue
    return None


def _extract_experience_ranges(text: str) -> list[tuple[int, Optional[int]]]:
    ranges: list[tuple[int, Optional[int]]] = []
    normalized = text.lower()
    for match in re.finditer(r"\b(\d{1,2})\s*[-–to]+\s*(\d{1,2})\s*(?:years?|yrs?)\b", normalized):
        low, high = int(match.group(1)), int(match.group(2))
        ranges.append((min(low, high), max(low, high)))
    for match in re.finditer(r"\b(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b", normalized):
        value = int(match.group(1))
        if "+" in match.group(0):
            ranges.append((value, None))
        else:
            ranges.append((value, value))
    return ranges


def _experience_matches(text: str, criteria: SearchCriteria) -> bool:
    if criteria.min_experience is None and criteria.max_experience is None:
        return True

    ranges = _extract_experience_ranges(text)
    if not ranges:
        return not criteria.strict_experience

    desired_min = criteria.min_experience if criteria.min_experience is not None else 0
    desired_max = criteria.max_experience if criteria.max_experience is not None else 99

    for found_min, found_max in ranges:
        found_max = found_max if found_max is not None else 99
        if found_min <= desired_max and found_max >= desired_min:
            return True
    return False


def _infer_role_category(title: str, description: str) -> Optional[str]:
    """Determine which role category a job belongs to.
    
    Strategy:
    1. First check the TITLE only — strong signal (e.g. "Backend Engineer" → backend)
    2. If no title match, check the description (weaker signal)
    
    Returns the category key (e.g. 'devops', 'backend') or None if unknown.
    """
    title_lower = title.lower()
    
    # Level 1: Check title only (strong signal)
    for category, patterns in _ROLE_CATEGORY_PATTERNS.items():
        if any(p.search(title_lower) for p in patterns):
            return category
    
    # Level 2: Check description (weaker — only if title was inconclusive)
    if description:
        desc_lower = description.lower()
        for category, patterns in _ROLE_CATEGORY_PATTERNS.items():
            if any(p.search(desc_lower) for p in patterns):
                return category
    
    return None


def _query_matches(title: str, description: str, criteria: SearchCriteria) -> bool:
    """Multi-level semantic query matching.
    
    Strategy (3 levels):
    
    Level 1 - Exact term match:
      Check if the query terms literally appear in the title/description.
    
    Level 2 - Role category match:
      Infer the role category from the job (e.g. 'devops', 'backend')
      and the query. If they match the same category, the job is relevant.
      This catches: "DevOps Engineer" -> "SRE", "Platform Engineer", "Cloud Engineer"
    
    Level 3 - General tech role fallback:
      If the job matches ANY tech role keyword, let it through.
      This is the broadest fallback.
    """
    terms = criteria.query_terms
    
    # --- Level 1: Exact term match ---
    title_text = title.lower()
    combined = f"{title} {description}".lower()
    required_matches = max(1, min(2, len(terms)))
    title_hits = sum(1 for term in terms if term in title_text)
    combined_hits = sum(1 for term in terms if term in combined)
    
    # Level 1a: Title has exact query term match
    if title_hits >= 1:
        return True
    
    # Level 1b: Combined has enough exact term matches (non-strict mode)
    if not criteria.strict_title and combined_hits >= max(1, required_matches - 1):
        return True
    
    # --- Level 2: Role category semantic match ---
    # Infer the role category from the job title/description
    # Uses title-first matching so stray words in descriptions don't cause false matches
    job_category = _infer_role_category(title, description)
    if job_category:
        # Infer the role category from the search query
        query_lower = criteria.query.lower()
        query_category = _infer_role_category(query_lower, query_lower)
        
        if query_category:
            # Same category = semantically related roles
            if job_category == query_category:
                return True
    
    # --- Level 3: General tech role fallback (non-strict only) ---
    if not criteria.strict_title:
        if is_relevant_role(title, description):
            return True
    
    return False


def _posted_within(posted_at: str | None, days: int | None) -> bool:
    if not days:
        return True
    posted = _parse_datetime(posted_at)
    if not posted:
        return True
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    return posted >= cutoff


def is_relevant_role(title: str, description: str) -> bool:
    combined = f"{title} {description}".lower()
    return _matches_any(combined, ROLE_KEYWORDS)


def is_junior_level(title: str, description: str) -> bool:
    combined = f"{title} {description}".lower()
    if _matches_any(combined, SENIOR_EXCLUDE):
        return False
    if _matches_any(combined, JUNIOR_KEYWORDS):
        return True
    title_lower = title.lower()
    if not _matches_any(title_lower, SENIOR_EXCLUDE):
        if _matches_any(combined, [r"\b0[\s-]?3\s*years?\b", r"\b1[\s-]?3\s*years?\b"]):
            return True
    return False


def is_global_remote_eligible(location: str, description: str) -> bool:
    combined = f"{location} {description}".lower()

    # First check for explicit global-remote positive signals in the description
    # These override location-based restrictions
    desc_lower = description.lower()
    global_positive_signals = [
        r"\bremote\b", r"\bworldwide\b", r"\banywhere\b", r"\bglobal\b",
        r"\binternational\b", r"\bopen to all\b", r"\bno location restriction\b",
    ]
    if any(re.search(p, desc_lower, re.I) for p in global_positive_signals):
        # But still respect explicit restrictions in the same text
        explicit_restrictions_text = [
            r"\bus\s*only\b", r"\busa\s*only\b", r"\bunited\s*states\s*only\b",
        ]
        if not any(re.search(p, desc_lower, re.I) for p in explicit_restrictions_text):
            return True

    # Check explicit location-based restrictions
    explicit_restrictions = [
        r"\bus\s*only\b",
        r"\busa\s*only\b",
        r"\bunited\s*states\s*only\b",
        r"\beu\s*only\b",
        r"\beurope\s*only\b",
        r"\buk\s*only\b",
        r"\bcanada\s*only\b",
        r"\bindia\s*only\b",
        r"\bindia-only\b",
    ]
    
    if _matches_any(combined, explicit_restrictions):
        return False
    
    if _matches_any(combined, [r"\bhybrid\b", r"\bonsite\b", r"\bon-site\b", r"\bin-office\b", r"\bin office\b"]):
        return False
    
    if _matches_any(combined, REMOTE_POSITIVE):
        return True
    
    if re.search(r"\bremote\b", combined, re.I):
        return True
    
    if re.search(r"\bworldwide\b|\banywhere\b|\bglobal\b|\binternational\b", combined, re.I):
        return True
    
    # If location is a specific city but description suggests remote, give partial credit
    if description and len(description) > 100:
        cloud_tools = r"\baws\b|\bgcp\b|\bazure\b|\bkubernetes\b|\bdocker\b|\bterraform\b"
        if re.search(cloud_tools, description, re.I):
            return True
    
    return False


def is_not_indian_hq(company: str) -> bool:
    company_lower = company.lower().strip()
    for indian in INDIAN_HQ_COMPANIES:
        if indian in company_lower:
            return False
    if re.search(r"\b(india|pvt\.?\s*ltd|private limited)\b", company_lower):
        return False
    return True


def is_indian_specific_location(location: str, description: str) -> bool:
    """Check if the job location is a specific Indian city/region (not global-remote).
    
    Returns True if the job is tied to a specific Indian location like
    "Gurgaon", "Bangalore", "Noida", etc. — meaning it's not truly
    global-remote even if the company is non-Indian.
    """
    loc_lower = location.lower()
    desc_lower = description.lower()
    
    # If the description says "Remote", treat as non-Indian-specific
    # UNLESS the location is a specific Indian city
    has_remote_signal = bool(re.search(r"\bremote\b", desc_lower, re.I)) or \
                        _matches_any(desc_lower, REMOTE_POSITIVE)
    
    # Check for Indian city names — these are the strongest signal
    # and override remote signals in the description
    for city in INDIAN_CITIES:
        if city in loc_lower or city in desc_lower:
            return True
    
    # Check for Indian state/region keywords
    for state in INDIAN_STATE_KEYWORDS:
        if state in loc_lower or state in desc_lower:
            if not has_remote_signal:
                return True
    
    # Check for pincode patterns
    if _matches_any(f"{loc_lower} {desc_lower}", [
        r"\bpincode\b",
        r"\bpin\s*code\b",
        r"\bindian\s+(?:time|rupees|standard|subcontinent)",
    ]):
        return True
    
    # For generic "India" references, only flag if no remote signal
    if re.search(r"\bindia\b", loc_lower, re.I) and not has_remote_signal:
        return True
    
    return False


def passes_all_filters(
    job: RawJob,
    strict_junior: bool = False,
    criteria: SearchCriteria | None = None,
) -> bool:
    criteria = criteria or SearchCriteria(max_experience=2 if strict_junior else None)
    desc = job.description or ""
    loc = job.location or ""
    combined = f"{job.title} {desc} {loc}"

    # Filter out non-English jobs (disabled: langdetect is too slow for real-time scraping)
    # if desc and len(desc) > 50 and not is_english_text(desc):
    #     logger.debug("Filter rejected (non-English): %s - %s", job.title, job.company)
    #     return False
    
    # Filter out likely fake jobs
    if is_likely_fake_job(job.title, desc, job.company):
        logger.debug("Filter rejected (fake job): %s - %s", job.title, job.company)
        return False

    # Must match the query/profile
    if not _query_matches(job.title, desc, criteria):
        logger.debug("Filter rejected (query mismatch): %s - %s", job.title, job.company)
        return False
    
    # Experience level check
    if strict_junior and not is_junior_level(job.title, desc):
        logger.debug("Filter rejected (not junior): %s - %s", job.title, job.company)
        return False
    if not _experience_matches(combined, criteria):
        logger.debug("Filter rejected (experience mismatch): %s - %s", job.title, job.company)
        return False
    
    # Senior exclusion for junior roles
    if criteria.max_experience is not None and criteria.max_experience <= 2:
        if _matches_any(combined, SENIOR_EXCLUDE):
            logger.debug("Filter rejected (senior role for junior search): %s - %s", job.title, job.company)
            return False
    
    # Remote eligibility
    if criteria.remote_only:
        is_remote = is_global_remote_eligible(loc, desc)
        is_explicitly_remote = re.search(r"\bremote\b", f"{job.title} {loc} {desc}", re.I)
        
        if not (is_remote or is_explicitly_remote or not loc):
            logger.debug("Filter rejected (not remote): %s - %s (location: %s)", job.title, job.company, loc)
            return False
    
    # Region eligibility
    if criteria.global_or_india:
        eligibility = infer_region_eligibility(loc, desc)
        if eligibility == "Unknown":
            is_explicitly_remote = re.search(r"\bremote\b", f"{loc} {desc}", re.I)
            if not is_explicitly_remote:
                logger.debug("Filter rejected (unknown region): %s - %s (location: %s)", job.title, job.company, loc)
                return False
    
    # Exclude Indian HQ companies
    if criteria.exclude_indian_hq and not is_not_indian_hq(job.company):
        logger.debug("Filter rejected (Indian HQ): %s - %s", job.title, job.company)
        return False
    
    # Exclude jobs at specific Indian locations (e.g. "Gurgaon", "Bangalore")
    # even if the company is non-Indian. A job in Gurgaon = not global-remote.
    if criteria.exclude_indian_hq and is_indian_specific_location(loc, desc):
        logger.debug("Filter rejected (Indian location): %s - %s (location: %s)", job.title, job.company, loc)
        return False
    
    # Posted date check
    if not _posted_within(job.posted_at, criteria.posted_within_days):
        logger.debug("Filter rejected (too old): %s - %s (posted: %s)", job.title, job.company, job.posted_at)
        return False
    
    return True


def extract_tech_stack(text: str) -> List[str]:
    found: Set[str] = set()
    for tech, patterns in TECH_STACK_MAP.items():
        if _matches_any(text, patterns):
            found.add(tech)
    return sorted(found)


def infer_experience_level(title: str, description: str) -> str:
    combined = f"{title} {description}".lower()
    if _matches_any(combined, [r"\bintern\b", r"\btrainee\b"]):
        return "Intern"
    if _matches_any(combined, JUNIOR_KEYWORDS):
        return "Junior (0-2 years)"
    if _matches_any(combined, SENIOR_EXCLUDE):
        return "Senior (excluded)"
    return "Mid-level"


def infer_company_size(company: str, description: str) -> str:
    combined = f"{company} {description}".lower()
    enterprise = [
        r"\bgoogle\b", r"\bamazon\b", r"\bmeta\b", r"\bmicrosoft\b",
        r"\bapple\b", r"\bnetflix\b", r"\bspotify\b", r"\bstripe\b",
        r"\buber\b", r"\bairbnb\b", r"\bsalesforce\b",
    ]
    if _matches_any(combined, enterprise):
        return "Enterprise"
    if _matches_any(combined, [r"\bstartup\b", r"\bseed\b", r"\bseries a\b"]):
        return "Startup"
    return "Mid-size"


def infer_region_eligibility(location: str, description: str) -> str:
    combined = f"{location} {description}".lower()
    if re.search(r"\bworldwide\b|\banywhere\b|\bglobal\b", combined, re.I):
        return "Worldwide"
    if re.search(r"\bindia\b", combined, re.I):
        return "India Eligible"
    if re.search(r"\bremote\b", combined, re.I):
        return "Remote (unspecified)"
    return "Unknown"


def is_english_text(text: str) -> bool:
    if not text or len(text.strip()) < 50:
        return True
    
    try:
        detected = langdetect.detect(text)
        return detected == 'en'
    except:
        return True


FAKE_JOB_PATTERNS = [
    r"\btelegram\b",
    r"\bwhatsapp\b",
    r"\bskype\b",
    r"\bdiscord\b.*\binterview\b",
    r"\bcrypto\b.*\bjob\b",
    r"\bbitcoin\b.*\bjob\b",
    r"\binvestment\b.*\bopportunity\b",
    r"\bwork from home\b.*\bdaily payment\b",
    r"\bno experience\b.*\bhigh salary\b",
    r"\bearn\b.*\bdaily\b",
    r"\bquick money\b",
    r"\beasy money\b",
    r"\bclick\b.*\bearn\b",
    r"\bsurvey\b.*\bjob\b",
    r"\bdata entry\b.*\bcaptcha\b",
    r"\bcopy paste\b.*\bjob\b",
    r"\bform filling\b.*\bjob\b",
    r"\bad posting\b.*\bjob\b",
    r"\bsocial media\b.*\bposting\b",
    r"\btelegram\b.*\bchannel\b",
    r"\bjoin\b.*\btelegram\b",
    r"\bmessage\b.*\btelegram\b",
    r"\bcontact\b.*\btelegram\b",
    r"\bwhatapp\b",
    r"\bwhats app\b",
]

SUSPICIOUS_COMPANY_PATTERNS = [
    r"\binc\b.*\bnew\b",
    r"\bstartup\b.*\bhiring\b.*\bimmediately\b",
    r"\burgent\b.*\bhiring\b",
    r"\bimmediate\b.*\bjoin\b",
    r"\bno interview\b",
    r"\bno resume\b",
    r"\bno qualification\b",
]

def is_likely_fake_job(title: str, description: str, company: str = "") -> bool:
    combined = f"{title} {description} {company}".lower()
    
    if _matches_any(combined, FAKE_JOB_PATTERNS):
        return True
    
    if _matches_any(combined, SUSPICIOUS_COMPANY_PATTERNS):
        return True
    
    urgency_count = len(re.findall(r"\burgent\b|\bimmediate\b|\basap\b|\btoday\b", combined))
    if urgency_count >= 3:
        return True
    
    if re.search(r"\b\d+.*\bdollar\b.*\bdaily\b", combined):
        return True
    
    return False


def expand_query(query: str, max_terms: int = 3) -> str:
    """Expand a search query to include related role titles.
    
    Uses the ROLE_CATEGORIES taxonomy to find related terms for the
    same role category. This helps scrapers find semantically related jobs
    (e.g. searching "DevOps Engineer" also matches "SRE", "Platform Engineer").
    
    Args:
        query: The original search query (e.g. "DevOps Engineer")
        max_terms: Maximum number of expanded terms to include (default 3)
        
    Returns:
        Expanded query string (e.g. "DevOps Engineer SRE Platform Engineer")
    """
    query_lower = query.lower()
    
    for category, data in ROLE_CATEGORIES.items():
        if any(kw in query_lower for kw in data["keywords"]):
            # Collect unique single-word keywords that aren't in the query
            seen = set()
            words = []
            query_words = set(query_lower.split())
            for kw in data["keywords"]:
                kw_lower = kw.lower()
                # Only single-word keywords (more effective for search engines)
                if " " in kw_lower:
                    continue
                if kw_lower in query_words or kw_lower in seen:
                    continue
                seen.add(kw_lower)
                words.append(kw)
            expanded = words[:max_terms]
            if expanded:
                return f"{query} {' '.join(expanded)}"
    
    return query