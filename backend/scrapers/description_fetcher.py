"""Deep description fetcher for job postings.

Many scrapers (especially RSS-based) return only truncated descriptions.
This module fetches the actual job page and extracts the full description text,
dramatically improving data quality for scoring, matching, and AI enrichment.
"""

import json
import logging
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List

import httpx
from bs4 import BeautifulSoup

from scrapers.schemas import NormalizedJob

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
]

BLOCKED_DOMAINS = [
    "linkedin.com", "glassdoor.com", "twitter.com", "x.com",
    "facebook.com", "instagram.com", "indeed.com/viewjob",
]

DESCRIPTION_MIN_LENGTH = 100


def _is_blocked_domain(url: str) -> bool:
    url_lower = url.lower()
    return any(d in url_lower for d in BLOCKED_DOMAINS)


def extract_description_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        tag.decompose()

    # Strategy 1: JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict):
                desc = data.get("description") or ""
                if len(desc) > DESCRIPTION_MIN_LENGTH:
                    return desc
            elif isinstance(data, list):
                for item in data:
                    desc = item.get("description") or ""
                    if len(desc) > DESCRIPTION_MIN_LENGTH:
                        return desc
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass

    # Strategy 2: Common job description container selectors
    selectors = [
        '[class*="description"]', '[class*="details"]',
        '[class*="job-body"]', '[class*="posting"]',
        '[class*="job-detail"]', '[id*="description"]',
        '[id*="job-detail"]', "article", '[data-testid*="description"]',
        ".show-more__content", '[class*="content"]',
    ]
    for selector in selectors:
        elements = soup.select(selector)
        for elem in elements:
            text = elem.get_text(separator=" ", strip=True)
            text = re.sub(r"\s+", " ", text)
            if len(text) > DESCRIPTION_MIN_LENGTH:
                return text

    # Strategy 3: Main content
    for tag in ["main", "article", "section"]:
        elem = soup.find(tag)
        if elem:
            text = elem.get_text(separator=" ", strip=True)
            text = re.sub(r"\s+", " ", text)
            if len(text) > DESCRIPTION_MIN_LENGTH:
                return text

    # Strategy 4: Body
    body = soup.find("body")
    if body:
        text = body.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 40]
        text = " ".join(lines)
        if len(text) > DESCRIPTION_MIN_LENGTH:
            return text

    return ""


def fetch_description(url: str, timeout: int = 15) -> Optional[str]:
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
    }

    try:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            encoding = "utf-8"
            if "charset=" in content_type:
                encoding = content_type.split("charset=")[-1].split(";")[0].strip()

            html = response.content.decode(encoding, errors="replace")
            description = extract_description_from_html(html)

            if description and len(description) >= DESCRIPTION_MIN_LENGTH:
                logger.debug(f"Fetched {len(description)} chars from {url}")
                return description

            logger.debug(f"Could not extract meaningful description from {url}")
            return None

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            logger.debug(f"Blocked (403) fetching {url}")
        else:
            logger.debug(f"HTTP {e.response.status_code} fetching {url}")
        return None
    except httpx.TimeoutException:
        logger.debug(f"Timeout fetching {url}")
        return None
    except Exception as e:
        logger.debug(f"Error fetching {url}: {e}")
        return None


def enrich_descriptions(
    jobs: List[NormalizedJob],
    max_workers: int = 5,
    delay: float = 0.3,
    min_length: int = DESCRIPTION_MIN_LENGTH,
) -> List[NormalizedJob]:
    jobs_to_fetch = [
        j for j in jobs
        if (not j.description or len(j.description) < min_length)
        and j.url
        and not _is_blocked_domain(j.url)
    ]

    if not jobs_to_fetch:
        logger.info("All jobs already have full descriptions — skipping fetch")
        return jobs

    logger.info(
        f"Fetching descriptions for {len(jobs_to_fetch)}/{len(jobs)} jobs "
        f"(workers={max_workers}, delay={delay}s)"
    )

    fetched_count = 0
    lock = __import__("threading").Lock()

    def _fetch(job: NormalizedJob) -> None:
        nonlocal fetched_count
        description = fetch_description(job.url)
        if description:
            with lock:
                job.description = description
                fetched_count += 1
        time.sleep(delay)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch, job): job for job in jobs_to_fetch}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logger.error(f"Description fetch error: {e}")

    logger.info(f"Fetched {fetched_count}/{len(jobs_to_fetch)} descriptions successfully")
    return jobs
