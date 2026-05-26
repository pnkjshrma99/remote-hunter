"""Smart filtering for runtime job searches."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Set
import langdetect

# Role niches we care about - expanded to cover more categories
ROLE_KEYWORDS = [
    # DevOps & SRE
    r"\bdevops\b",
    r"\bsre\b",
    r"\bsite reliability\b",
    r"\bplatform engineer",
    r"\binfrastructure engineer",
    r"\bcloud engineer",
    r"\bcloud ops\b",
    r"\breliability engineer",
    r"\bsystems engineer\b",
    r"\bplatform ops\b",
    # Backend
    r"\bbackend engineer",
    r"\bback-end engineer",
    r"\bbackend developer",
    r"\bback-end developer",
    r"\bserver engineer",
    r"\bserver developer",
    r"\bapi engineer",
    r"\bapi developer",
    # Frontend
    r"\bfrontend engineer",
    r"\bfront-end engineer",
    r"\bfrontend developer",
    r"\bfront-end developer",
    r"\bui engineer",
    r"\bux engineer",
    r"\bweb developer",
    r"\bweb engineer",
    # Full Stack
    r"\bfull[-\s]?stack engineer",
    r"\bfull[-\s]?stack developer",
    # Data Science
    r"\bdata scientist",
    r"\bdata engineer",
    r"\bml engineer",
    r"\bmachine learning engineer",
    r"\bai engineer",
    r"\bartificial intelligence engineer",
    # Mobile
    r"\bmobile engineer",
    r"\bmobile developer",
    r"\bios engineer",
    r"\bandroid engineer",
    r"\bandroid developer",
    # QA & Testing
    r"\bqa engineer",
    r"\bquality assurance",
    r"\btest engineer",
    r"\bautomation engineer",
    # Security
    r"\bsecurity engineer",
    r"\bdevsecops",
    r"\bcybersecurity",
    # General Software
    r"\bsoftware engineer",
    r"\bsoftware developer",
    r"\bdeveloper",
    r"\bengineer",
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
    r"\bi\b",  # intern - careful, matched with word boundaries below
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
    r"\bindia\b",
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

# Known Indian HQ companies to exclude (partial list - extensible)
INDIAN_HQ_COMPANIES = {
    "tcs", "tata consultancy", "infosys", "wipro", "hcl", "tech mahindra",
    "cognizant", "mindtree", "mphasis", "ltimindtree", "lti", "persistent",
    "zoho", "freshworks", "flipkart", "paytm", "ola", "swiggy", "zomato",
    "byju", "razorpay", "phonepe", "cred", "meesho", "inmobi", "mu sigma",
    "capgemini india", "accenture india", "genpact", "mphasis", "cyient",
    "hexaware", "birlasoft", "niit", "sonata", "mastek", "zensar",
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
    job_profile_id: Optional[str] = None  # Reference to predefined job profile
    min_experience: Optional[int] = None
    max_experience: Optional[int] = 2
    posted_within_days: Optional[int] = 14
    remote_only: bool = True
    global_or_india: bool = True
    exclude_indian_hq: bool = True
    strict_experience: bool = False
    strict_title: bool = True
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


def _query_matches(title: str, description: str, criteria: SearchCriteria) -> bool:
    terms = criteria.query_terms
    if not terms:
        return is_relevant_role(title, description)

    title_text = title.lower()
    combined = f"{title} {description}".lower()
    required_matches = max(1, min(2, len(terms)))
    title_hits = sum(1 for term in terms if term in title_text)
    combined_hits = sum(1 for term in terms if term in combined)
    
    # More flexible matching: allow description matches if strict_title is False
    if criteria.strict_title:
        return title_hits >= 1
    # Allow combined matches (title + description) with lower threshold
    return combined_hits >= max(1, required_matches - 1)


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
    # Allow roles without explicit seniority if title doesn't say senior
    title_lower = title.lower()
    if not _matches_any(title_lower, SENIOR_EXCLUDE):
        # Permissive: entry DevOps roles often omit "junior" in title
        if _matches_any(combined, [r"\b0[\s-]?3\s*years?\b", r"\b1[\s-]?3\s*years?\b"]):
            return True
    return False


def is_global_remote_eligible(location: str, description: str) -> bool:
    combined = f"{location} {description}".lower()
    
    # First check for explicit location restrictions that would disqualify
    # Only exclude if it's explicitly "only" a specific region
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
    
    # Check for hybrid/onsite - these are not fully remote
    if _matches_any(combined, [r"\bhybrid\b", r"\bonsite\b", r"\bon-site\b", r"\bin-office\b", r"\bin office\b"]):
        return False
    
    # Check for positive remote indicators
    if _matches_any(combined, REMOTE_POSITIVE):
        return True
    
    # Default permissive if just says remote with no restrictions
    if re.search(r"\bremote\b", combined, re.I):
        return True
    
    # If location mentions multiple countries or "worldwide", allow it
    if re.search(r"\bworldwide\b|\banywhere\b|\bglobal\b|\binternational\b", combined, re.I):
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


def passes_all_filters(
    job: RawJob,
    strict_junior: bool = False,
    criteria: SearchCriteria | None = None,
) -> bool:
    """
    Filter jobs based on criteria.
    
    Filtering Strategy:
    - Strict on relevance: Must match the job title/profile
    - Moderate on experience: Allow ranges that overlap with desired range
    - Permissive on location: Allow any "Remote" job unless explicitly restricted
    - Moderate on freshness: Respect posted_within_days setting (14 days = reasonable)
    """
    criteria = criteria or SearchCriteria(max_experience=2 if strict_junior else None)
    desc = job.description or ""
    loc = job.location or ""
    combined = f"{job.title} {desc} {loc}"

    # Filter out non-English jobs (good quality control)
    if desc and len(desc) > 50 and not is_english_text(desc):
        return False
    
    # Filter out likely fake jobs (good quality control)
    if is_likely_fake_job(job.title, desc, job.company):
        return False

    # Must match the query/profile (strict)
    if not _query_matches(job.title, desc, criteria):
        return False
    
    # Experience level check
    if strict_junior and not is_junior_level(job.title, desc):
        return False
    if not _experience_matches(combined, criteria):
        return False
    
    # Senior exclusion for junior roles
    if criteria.max_experience is not None and criteria.max_experience <= 2:
        if _matches_any(combined, SENIOR_EXCLUDE):
            return False
    
    # Remote eligibility (permissive for "Remote" jobs)
    if criteria.remote_only:
        # Allow if it explicitly says remote, or if location is not specified
        is_remote = is_global_remote_eligible(loc, desc)
        is_explicitly_remote = re.search(r"\bremote\b", f"{job.title} {loc} {desc}", re.I)
        
        if not (is_remote or is_explicitly_remote or not loc):
            return False
    
    # Region eligibility (permissive - only reject if explicitly restricted)
    if criteria.global_or_india:
        eligibility = infer_region_eligibility(loc, desc)
        # Allow Unknown if job says Remote (means no geographic restriction)
        if eligibility == "Unknown":
            is_explicitly_remote = re.search(r"\bremote\b", f"{loc} {desc}", re.I)
            if not is_explicitly_remote:
                # Only reject if it's not remote and region is unknown
                return False
    
    # Exclude Indian HQ companies only if specified
    if criteria.exclude_indian_hq and not is_not_indian_hq(job.company):
        return False
    
    # Posted date check (14 days is reasonable, not aggressive)
    if not _posted_within(job.posted_at, criteria.posted_within_days):
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
    """
    Detect if text is in English using langdetect.
    Returns True if English, False otherwise.
    Falls back to True if detection fails.
    """
    if not text or len(text.strip()) < 50:
        return True  # Too short to detect reliably, allow it
    
    try:
        detected = langdetect.detect(text)
        return detected == 'en'
    except:
        return True  # If detection fails, allow it


# Fake job detection patterns
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
    """
    Detect likely fake/scam job postings based on suspicious patterns.
    Returns True if likely fake, False otherwise.
    """
    combined = f"{title} {description} {company}".lower()
    
    # Check for fake job patterns
    if _matches_any(combined, FAKE_JOB_PATTERNS):
        return True
    
    # Check for suspicious company patterns
    if _matches_any(combined, SUSPICIOUS_COMPANY_PATTERNS):
        return True
    
    # Check for excessive use of urgency
    urgency_count = len(re.findall(r"\burgent\b|\bimmediate\b|\basap\b|\btoday\b", combined))
    if urgency_count >= 3:
        return True
    
    # Check for unrealistic salary promises
    if re.search(r"\b\d+.*\bdollar\b.*\bdaily\b", combined):
        return True
    
    return False

