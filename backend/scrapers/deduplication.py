"""Deduplication system for jobs.

Implements three levels of deduplication:
1. Exact dedupe using stable IDs
2. Fuzzy dedupe using normalized title + company + URL
3. Near-duplicate detection using token similarity
"""

import hashlib
import re
import logging
from typing import List, Dict, Set, Tuple, Optional
from difflib import SequenceMatcher
from collections import defaultdict

from scrapers.schemas import NormalizedJob

logger = logging.getLogger(__name__)


class JobDeduplicator:
    """Handles job deduplication at multiple levels."""
    
    def __init__(
        self,
        enable_exact: bool = True,
        enable_fuzzy: bool = True,
        enable_near_duplicate: bool = True,
        fuzzy_threshold: float = 0.85,
        near_duplicate_threshold: float = 0.9
    ):
        self.enable_exact = enable_exact
        self.enable_fuzzy = enable_fuzzy
        self.enable_near_duplicate = enable_near_duplicate
        self.fuzzy_threshold = fuzzy_threshold
        self.near_duplicate_threshold = near_duplicate_threshold
        
        # Track seen jobs for deduplication
        self._seen_external_ids: Set[str] = set()
        self._seen_fuzzy_signatures: Dict[str, List[NormalizedJob]] = defaultdict(list)
        self._seen_near_duplicates: Dict[str, List[NormalizedJob]] = defaultdict(list)
    
    def deduplicate(self, jobs: List[NormalizedJob]) -> List[NormalizedJob]:
        """Run all deduplication levels and return unique jobs.
        
        Args:
            jobs: List of jobs to deduplicate
            
        Returns:
            List of unique jobs with duplicate flags set
        """
        logger.info(f"Deduplicating {len(jobs)} jobs")
        
        # Level 1: Exact dedupe by external_id
        if self.enable_exact:
            jobs = self._exact_deduplicate(jobs)
            logger.info(f"After exact dedupe: {len(jobs)} jobs")
        
        # Level 2: Fuzzy dedupe by normalized signature
        if self.enable_fuzzy:
            jobs = self._fuzzy_deduplicate(jobs)
            logger.info(f"After fuzzy dedupe: {len(jobs)} jobs")
        
        # Level 3: Near-duplicate detection
        if self.enable_near_duplicate:
            jobs = self._near_duplicate_deduplicate(jobs)
            logger.info(f"After near-duplicate dedupe: {len(jobs)} jobs")
        
        return jobs
    
    def _exact_deduplicate(self, jobs: List[NormalizedJob]) -> List[NormalizedJob]:
        """Exact deduplication using external_id."""
        unique_jobs = []
        seen_ids = set()
        
        for job in jobs:
            if job.external_id not in seen_ids:
                seen_ids.add(job.external_id)
                unique_jobs.append(job)
            else:
                job.is_duplicate = True
                job.duplicate_group_id = job.external_id
                logger.debug(f"Exact duplicate: {job.external_id}")
        
        return unique_jobs
    
    def _fuzzy_deduplicate(self, jobs: List[NormalizedJob]) -> List[NormalizedJob]:
        """Fuzzy deduplication using normalized title + company + URL."""
        unique_jobs = []
        signature_groups: Dict[str, List[NormalizedJob]] = defaultdict(list)
        
        for job in jobs:
            signature = self._generate_fuzzy_signature(job)
            signature_groups[signature].append(job)
        
        for signature, group in signature_groups.items():
            if len(group) == 1:
                unique_jobs.extend(group)
            else:
                # Keep the job with highest relevance score
                group.sort(key=lambda j: j.relevance_score, reverse=True)
                unique_jobs.append(group[0])
                
                # Mark others as duplicates
                for dup_job in group[1:]:
                    dup_job.is_duplicate = True
                    dup_job.duplicate_group_id = signature
                    logger.debug(f"Fuzzy duplicate: {signature}")
        
        return unique_jobs
    
    def _near_duplicate_deduplicate(self, jobs: List[NormalizedJob]) -> List[NormalizedJob]:
        """Near-duplicate detection using token similarity."""
        unique_jobs = []
        processed: List[NormalizedJob] = []
        
        for job in jobs:
            is_near_duplicate = False
            best_match_score = 0.0
            best_match_job = None
            
            for existing_job in processed:
                similarity = self._calculate_similarity(job, existing_job)
                if similarity >= self.near_duplicate_threshold:
                    is_near_duplicate = True
                    if similarity > best_match_score:
                        best_match_score = similarity
                        best_match_job = existing_job
            
            if is_near_duplicate and best_match_job:
                job.is_duplicate = True
                # Use the existing job's duplicate_group_id or create new one
                if best_match_job.duplicate_group_id:
                    job.duplicate_group_id = best_match_job.duplicate_group_id
                else:
                    group_id = self._generate_near_duplicate_id(job, best_match_job)
                    best_match_job.duplicate_group_id = group_id
                    job.duplicate_group_id = group_id
                logger.debug(f"Near-duplicate: similarity={best_match_score:.2f}")
            else:
                unique_jobs.append(job)
                processed.append(job)
        
        return unique_jobs
    
    def _generate_fuzzy_signature(self, job: NormalizedJob) -> str:
        """Generate fuzzy signature for job."""
        # Normalize title and company
        normalized_title = self._normalize_text(job.title)
        normalized_company = self._normalize_text(job.company)
        
        # Normalize URL (remove query params, tracking)
        normalized_url = self._normalize_url(job.url)
        
        # Create signature
        signature_str = f"{normalized_title}|{normalized_company}|{normalized_url}"
        return hashlib.sha256(signature_str.encode()).hexdigest()[:16]
    
    def _generate_near_duplicate_id(self, job1: NormalizedJob, job2: NormalizedJob) -> str:
        """Generate ID for near-duplicate group."""
        combined = f"{job1.external_id}|{job2.external_id}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""
        
        # Lowercase
        text = text.lower()
        
        # Remove special characters, keep alphanumeric and spaces
        text = re.sub(r"[^a-z0-9\s]", "", text)
        
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text).strip()
        
        return text
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison."""
        if not url:
            return ""
        
        # Remove query parameters and fragments
        url = re.sub(r"[?#].*$", "", url)
        
        # Remove trailing slash
        url = url.rstrip("/")
        
        return url.lower()
    
    def _calculate_similarity(self, job1: NormalizedJob, job2: NormalizedJob) -> float:
        """Calculate similarity between two jobs."""
        # Compare titles
        title_similarity = SequenceMatcher(
            None,
            self._normalize_text(job1.title),
            self._normalize_text(job2.title)
        ).ratio()
        
        # Compare companies
        company_similarity = SequenceMatcher(
            None,
            self._normalize_text(job1.company),
            self._normalize_text(job2.company)
        ).ratio()
        
        # Compare descriptions (first 500 chars)
        desc1 = self._normalize_text(job1.description[:500])
        desc2 = self._normalize_text(job2.description[:500])
        desc_similarity = SequenceMatcher(None, desc1, desc2).ratio()
        
        # Weighted average
        # Title is most important, company second, description third
        similarity = (
            title_similarity * 0.5 +
            company_similarity * 0.3 +
            desc_similarity * 0.2
        )
        
        return similarity
    
    def reset(self):
        """Reset deduplication state."""
        self._seen_external_ids.clear()
        self._seen_fuzzy_signatures.clear()
        self._seen_near_duplicates.clear()


def deduplicate_jobs(
    jobs: List[NormalizedJob],
    enable_exact: bool = True,
    enable_fuzzy: bool = True,
    enable_near_duplicate: bool = True,
    fuzzy_threshold: float = 0.85,
    near_duplicate_threshold: float = 0.9
) -> List[NormalizedJob]:
    """Convenience function to deduplicate jobs.
    
    Args:
        jobs: List of jobs to deduplicate
        enable_exact: Enable exact deduplication
        enable_fuzzy: Enable fuzzy deduplication
        enable_near_duplicate: Enable near-duplicate detection
        fuzzy_threshold: Threshold for fuzzy matching (0-1)
        near_duplicate_threshold: Threshold for near-duplicate (0-1)
    
    Returns:
        List of unique jobs
    """
    deduplicator = JobDeduplicator(
        enable_exact=enable_exact,
        enable_fuzzy=enable_fuzzy,
        enable_near_duplicate=enable_near_duplicate,
        fuzzy_threshold=fuzzy_threshold,
        near_duplicate_threshold=near_duplicate_threshold
    )
    return deduplicator.deduplicate(jobs)


def generate_duplicate_signature(title: str, company: str, description: str) -> str:
    """Generate a signature for duplicate detection (legacy compatibility).
    
    This function is kept for backward compatibility with existing code.
    """
    normalized_title = re.sub(r"[^a-zA-Z0-9]", "", title.lower())
    normalized_company = re.sub(r"[^a-zA-Z0-9]", "", company.lower())
    normalized_desc = re.sub(r"[^a-zA-Z0-9]", "", (description or "")[:200].lower())
    
    signature_str = f"{normalized_title}|{normalized_company}|{normalized_desc}"
    return hashlib.sha256(signature_str.encode()).hexdigest()[:16]
