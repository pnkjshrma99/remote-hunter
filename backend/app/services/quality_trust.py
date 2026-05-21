"""Quality and Trust features: seniority detection, duplicate detection, verified remote status."""

import hashlib
import re
from typing import Optional, Tuple
from collections import defaultdict

from scrapers.filters import JUNIOR_KEYWORDS, SENIOR_EXCLUDE, REMOTE_POSITIVE


def detect_seniority(title: str, description: str = "") -> str:
    """
    Detect seniority level from job title and description.
    Returns: 'junior', 'mid', 'senior', or 'unknown'
    """
    combined = f"{title} {description}".lower()
    
    # Check for senior indicators
    senior_patterns = [
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
    
    if any(re.search(p, combined, re.I) for p in senior_patterns):
        return "senior"
    
    # Check for junior indicators
    if any(re.search(p, combined, re.I) for p in JUNIOR_KEYWORDS):
        return "junior"
    
    # Check for mid-level indicators
    mid_patterns = [
        r"\b3[\s-]?5\s*years?\b",
        r"\b4[\s-]?6\s*years?\b",
        r"\bmid[\s-]?level\b",
        r"\bintermediate\b",
    ]
    
    if any(re.search(p, combined, re.I) for p in mid_patterns):
        return "mid"
    
    # Default to mid if no clear indicators
    return "mid"


def is_verified_remote(location: str, description: str = "", title: str = "") -> bool:
    """
    Determine if a job is verified as 100% remote.
    Checks for explicit remote-friendly indicators.
    """
    combined = f"{title} {description} {location}".lower()
    
    # Strong indicators of 100% remote
    verified_patterns = [
        r"\b100%\s*remote\b",
        r"\bfully remote\b",
        r"\bremote\s*-\s*global\b",
        r"\bremote\s*worldwide\b",
        r"\bwork from anywhere\b",
        r"\banywhere in the world\b",
        r"\bglobal remote\b",
        r"\bno location restriction\b",
        r"\blocation independent\b",
    ]
    
    if any(re.search(p, combined, re.I) for p in verified_patterns):
        return True
    
    # Check for negative indicators that would disqualify
    negative_patterns = [
        r"\bhybrid\b",
        r"\bon-site\b",
        r"\bonsite\b",
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
    ]
    
    if any(re.search(p, combined, re.I) for p in negative_patterns):
        return False
    
    # If it says remote without restrictions, consider it verified
    if re.search(r"\bremote\b", combined, re.I):
        return True
    
    return False


def generate_duplicate_signature(title: str, company: str, description: str = "") -> str:
    """
    Generate a signature for duplicate detection.
    Uses title and company (normalized) to identify potential duplicates.
    """
    # Normalize text
    normalized_title = re.sub(r'[^\w\s]', '', title.lower()).strip()
    normalized_company = re.sub(r'[^\w\s]', '', company.lower()).strip()
    
    # Create signature
    signature_text = f"{normalized_title}|{normalized_company}"
    
    # Hash for consistent ID
    return hashlib.md5(signature_text.encode()).hexdigest()


def detect_duplicates(jobs: list) -> dict[str, list[str]]:
    """
    Detect duplicate jobs across sources.
    Returns a dict mapping duplicate_group_id to list of job IDs.
    """
    # Group by signature
    signature_groups = defaultdict(list)
    
    for job in jobs:
        signature = generate_duplicate_signature(
            job.get('title', ''),
            job.get('company', ''),
            job.get('description', '')
        )
        signature_groups[signature].append(job.get('id'))
    
    # Filter to only actual duplicates (groups with > 1 job)
    duplicates = {
        sig: job_ids 
        for sig, job_ids in signature_groups.items() 
        if len(job_ids) > 1
    }
    
    return duplicates


def calculate_source_performance(
    source: str,
    total_scraped: int,
    total_matched: int,
    avg_response_time_ms: float = 0,
    duplicate_count: int = 0,
) -> dict:
    """
    Calculate performance metrics for a job source.
    """
    match_rate = (total_matched / total_scraped * 100) if total_scraped > 0 else 0
    duplicate_rate = (duplicate_count / total_scraped * 100) if total_scraped > 0 else 0
    
    return {
        "source": source,
        "total_scraped": total_scraped,
        "total_matched": total_matched,
        "match_rate": round(match_rate, 2),
        "duplicate_rate": round(duplicate_rate, 2),
        "avg_response_time_ms": round(avg_response_time_ms, 2),
    }


def extract_salary_range(salary_text: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Extract min and max salary from salary text.
    Returns (min_salary, max_salary) tuple.
    """
    if not salary_text:
        return None, None
    
    # Look for patterns like "$50,000 - $80,000", "50k-80k", etc.
    patterns = [
        r'[\$€£]?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*[-–to]+\s*[\$€£]?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)',
        r'(\d{1,3})k\s*[-–to]+\s*(\d{1,3})k',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, salary_text, re.I)
        if match:
            min_str = match.group(1).replace(',', '')
            max_str = match.group(2).replace(',', '')
            
            try:
                min_val = int(float(min_str))
                max_val = int(float(max_str))
                
                # Convert k to thousands
                if 'k' in salary_text.lower():
                    min_val *= 1000
                    max_val *= 1000
                
                return min_val, max_val
            except (ValueError, AttributeError):
                continue
    
    return None, None
