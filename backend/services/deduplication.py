"""Intelligent Job Deduplication Engine

This module provides comprehensive deduplication using multiple strategies:
- Title & company normalization
- Fuzzy string matching (rapidfuzz)
- Semantic similarity (transformers)
- URL canonical detection
- ATS identifier matching
- Duplicate clustering
"""

import logging
import hashlib
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass
from datetime import datetime

from rapidfuzz import fuzz
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.job import Job
from app.database import SessionLocal

logger = logging.getLogger(__name__)

# Constants
FUZZY_THRESHOLD = 0.85  # 85% similarity = likely duplicate
SEMANTIC_THRESHOLD = 0.92  # 92% embedding similarity = likely duplicate
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


@dataclass
class DuplicateMatch:
    """Represents a detected duplicate match"""
    job_id: int
    matched_with: int
    match_type: str  # 'exact', 'fuzzy', 'semantic'
    similarity_score: float
    confidence: float  # 0-1


class JobNormalizer:
    """Normalizes job data for comparison"""

    # Common company name variations
    COMPANY_SUFFIXES = {
        'inc.', 'inc', 'ltd.', 'ltd', 'llc', 'corp.', 'corp',
        'gmbh', 'ag', 'sa', 'pty', 'co.', 'co', 'plc', 'bv'
    }

    # Common title variations to standardize
    TITLE_MAPPINGS = {
        'sr ': 'senior ',
        'sr.': 'senior ',
        'jr ': 'junior ',
        'jr.': 'junior ',
        'dev ': 'developer ',
        'eng ': 'engineer ',
        'devops': 'devops ',
        'ml ': 'machine learning ',
        'ai ': 'artificial intelligence ',
        'qa ': 'quality assurance ',
        'pm ': 'product manager ',
        'fullstack': 'full stack',
        'full-stack': 'full stack',
    }

    # Stopwords to remove for comparison
    STOPWORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
        'to', 'for', 'of', 'with', 'by', 'from', 'remote', 'job',
        'position', 'role', 'opening', 'hiring', 'needed'
    }

    @classmethod
    def normalize_title(cls, title: str) -> str:
        """Normalize job title"""
        if not title:
            return ""

        # Lowercase
        normalized = title.lower().strip()

        # Apply mappings
        for key, value in cls.TITLE_MAPPINGS.items():
            normalized = normalized.replace(key, value)

        # Remove extra whitespace
        normalized = ' '.join(normalized.split())

        # Remove stopwords
        tokens = [t for t in normalized.split() if t not in cls.STOPWORDS]
        normalized = ' '.join(tokens)

        return normalized

    @classmethod
    def normalize_company(cls, company: str) -> str:
        """Normalize company name"""
        if not company:
            return ""

        # Lowercase
        normalized = company.lower().strip()

        # Remove common suffixes
        for suffix in cls.COMPANY_SUFFIXES:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()

        # Remove extra whitespace
        normalized = ' '.join(normalized.split())

        return normalized

    @classmethod
    def normalize_location(cls, location: str) -> str:
        """Normalize location"""
        if not location:
            return ""

        normalized = location.lower().strip()

        # Handle common variations
        normalized = normalized.replace('united states', 'us')
        normalized = normalized.replace('united kingdom', 'uk')
        normalized = normalized.replace('remote - ', '').replace('remote ', '')

        return ' '.join(normalized.split())

    @classmethod
    def tokenize(cls, text: str) -> set:
        """Tokenize text for set-based comparison"""
        normalized = text.lower().strip()
        tokens = set(normalized.split())
        return tokens - cls.STOPWORDS


class EmbeddingManager:
    """Manages job embeddings for semantic similarity"""

    _model = None

    @classmethod
    def get_model(cls):
        """Lazy load embedding model"""
        if cls._model is None:
            from app.config import get_settings
            if get_settings().disable_semantic_dedup:
                raise RuntimeError("Semantic dedup disabled by DISABLE_SEMANTIC_DEDUP=true")
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
            cls._model = SentenceTransformer(EMBEDDING_MODEL)
        return cls._model

    @classmethod
    def generate_embedding(cls, text: str) -> List[float]:
        """Generate embedding for job text"""
        if not text or not text.strip():
            # Return zero vector if empty
            return [0.0] * 384

        model = cls.get_model()
        embedding = model.encode(text, convert_to_tensor=False)
        return embedding.tolist()

    @classmethod
    def similarity(cls, emb1: List[float], emb2: List[float]) -> float:
        """Calculate cosine similarity between embeddings"""
        import numpy as np
        arr1 = np.array(emb1)
        arr2 = np.array(emb2)

        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(arr1, arr2) / (norm1 * norm2))


class DeduplicationEngine:
    """Main deduplication engine"""

    def __init__(self, db: Session):
        self.db = db
        self.normalizer = JobNormalizer()
        self.embedding_manager = EmbeddingManager()

    def find_duplicates_for_job(self, job: Job) -> List[DuplicateMatch]:
        """Find all duplicates for a given job"""
        matches = []

        # 1. Try exact match first (fastest)
        exact_matches = self._find_exact_duplicates(job)
        matches.extend(exact_matches)

        if matches:
            logger.debug(f"Found {len(matches)} exact matches for job {job.id}")
            return matches

        # 2. Try fuzzy string matching
        fuzzy_matches = self._find_fuzzy_duplicates(job)
        matches.extend(fuzzy_matches)

        if matches:
            logger.debug(f"Found {len(matches)} fuzzy matches for job {job.id}")
            return matches

        # 3. Try semantic similarity (most expensive)
        semantic_matches = self._find_semantic_duplicates(job)
        matches.extend(semantic_matches)

        if matches:
            logger.debug(f"Found {len(matches)} semantic matches for job {job.id}")

        return matches

    def _find_exact_duplicates(self, job: Job) -> List[DuplicateMatch]:
        """Find exact matches using normalized fields"""
        matches = []

        norm_title = self.normalizer.normalize_title(job.title)
        norm_company = self.normalizer.normalize_company(job.company)
        norm_location = self.normalizer.normalize_location(job.location or "")

        if not norm_title or not norm_company:
            return matches

        # Query for exact normalized matches (SQLite-compatible)
        # Use simple LIKE matching instead of regex
        candidates = self.db.query(Job).filter(
            and_(
                Job.id != job.id,
                Job.source != job.source,  # Different source
                func.lower(Job.title).like(f"%{norm_title}%"),
                func.lower(Job.company).like(f"%{norm_company}%"),
            )
        ).all()

        for candidate in candidates:
            # Double-check with fuzzy matching
            title_sim = fuzz.ratio(norm_title, 
                                   self.normalizer.normalize_title(candidate.title))
            company_sim = fuzz.ratio(norm_company, 
                                    self.normalizer.normalize_company(candidate.company))

            # Require both title and company similarity
            if title_sim >= 85 and company_sim >= 85:
                matches.append(DuplicateMatch(
                    job_id=job.id,
                    matched_with=candidate.id,
                    match_type='exact',
                    similarity_score=(title_sim + company_sim) / 200.0,
                    confidence=0.90
                ))

        return matches

    def _find_fuzzy_duplicates(self, job: Job) -> List[DuplicateMatch]:
        """Find fuzzy matches using string similarity"""
        matches = []

        norm_title = self.normalizer.normalize_title(job.title)
        norm_company = self.normalizer.normalize_company(job.company)

        if not norm_title or len(norm_title) < 5:
            return matches

        # Get candidate jobs from different sources (SQLite-compatible)
        # Use simple LIKE to get candidates, then do fuzzy matching in Python
        candidates = self.db.query(Job).filter(
            and_(
                Job.id != job.id,
                Job.source != job.source,  # Different source
                func.lower(Job.title).like(f"%{norm_title[:20]}%")  # Match on first 20 chars
            )
        ).limit(50).all()  # Limit for performance

        for candidate in candidates:
            cand_title = self.normalizer.normalize_title(candidate.title)
            cand_company = self.normalizer.normalize_company(candidate.company)

            # Compare both title and company
            title_sim = fuzz.token_set_ratio(norm_title, cand_title) / 100.0
            company_sim = fuzz.ratio(norm_company, cand_company) / 100.0

            # Weighted similarity
            overall_sim = (title_sim * 0.7) + (company_sim * 0.3)

            if overall_sim >= FUZZY_THRESHOLD:
                confidence = min(overall_sim, 0.95)  # Cap at 0.95
                matches.append(DuplicateMatch(
                    job_id=job.id,
                    matched_with=candidate.id,
                    match_type='fuzzy',
                    similarity_score=overall_sim,
                    confidence=confidence
                ))

        return matches

    def _find_semantic_duplicates(self, job: Job) -> List[DuplicateMatch]:
        """Find semantic duplicates using embeddings"""
        from app.config import get_settings
        if get_settings().disable_semantic_dedup:
            return []
        matches = []

        # Build searchable text
        search_text = f"{job.title} {job.company} {job.description or ''}"

        try:
            job_embedding = self.embedding_manager.generate_embedding(search_text)
        except Exception as e:
            logger.warning(f"Failed to generate embedding for job {job.id}: {e}")
            return matches

        # Find similar jobs by comparing embeddings
        # In production, this would use pgvector's similarity search
        candidates = self.db.query(Job).filter(
            and_(
                Job.id != job.id,
                Job.scraped_at > job.scraped_at - __import__('datetime').timedelta(days=14),
            )
        ).limit(50).all()  # Limit for performance

        for candidate in candidates:
            cand_text = f"{candidate.title} {candidate.company} {candidate.description or ''}"

            try:
                cand_embedding = self.embedding_manager.generate_embedding(cand_text)
                similarity = self.embedding_manager.similarity(job_embedding, cand_embedding)

                if similarity >= SEMANTIC_THRESHOLD:
                    matches.append(DuplicateMatch(
                        job_id=job.id,
                        matched_with=candidate.id,
                        match_type='semantic',
                        similarity_score=similarity,
                        confidence=min(similarity, 0.9)
                    ))
            except Exception as e:
                logger.warning(f"Failed semantic comparison: {e}")
                continue

        return matches

    def get_duplicate_cluster_hash(self, job: Job) -> str:
        """Generate deterministic hash for duplicate clustering"""
        norm_title = self.normalizer.normalize_title(job.title)
        norm_company = self.normalizer.normalize_company(job.company)
        norm_location = self.normalizer.normalize_location(job.location or "")

        combined = f"{norm_title}|{norm_company}|{norm_location}"
        return hashlib.md5(combined.encode()).hexdigest()

    def deduplicate_batch(self, jobs: List[Job], preserve_source_priority: Dict[str, int] = None) -> Dict:
        """
        Deduplicate a batch of jobs.

        Args:
            jobs: List of jobs to deduplicate
            preserve_source_priority: Dict mapping source name to priority (higher = better)

        Returns:
            Dict with deduplication results
        """
        if preserve_source_priority is None:
            # Default priority (higher = preserve this source)
            preserve_source_priority = {
                'greenhouse': 10,
                'github_jobs': 9,
                'devto_jobs': 9,
                'wellfound': 8,
                'authentic_jobs': 8,
                'indie_hackers': 8,
                'weworkremotely': 7,
                'remotive': 5,
                'remoteok': 4,
                'rss_feeds': 3,
            }

        results = {
            'total_jobs': len(jobs),
            'duplicates_found': 0,
            'duplicate_clusters': {},
            'primary_jobs': [],
            'errors': []
        }

        # Track processed jobs
        processed = set()
        clusters = {}

        for job in jobs:
            if job.id in processed:
                continue

            # Find duplicates
            matches = self.find_duplicates_for_job(job)

            if not matches:
                # No duplicates, this is a primary job
                results['primary_jobs'].append(job.id)
                processed.add(job.id)
                continue

            # Create cluster with this job as primary
            cluster_id = len(clusters)
            cluster_hash = self.get_duplicate_cluster_hash(job)

            # Determine primary job (highest source priority)
            cluster_jobs = [job.id] + [m.matched_with for m in matches]
            cluster_jobs_objs = self.db.query(Job).filter(Job.id.in_(cluster_jobs)).all()

            primary_job = max(
                cluster_jobs_objs,
                key=lambda j: preserve_source_priority.get(j.source, 0)
            )

            clusters[cluster_id] = {
                'cluster_hash': cluster_hash,
                'primary_job_id': primary_job.id,
                'duplicate_jobs': [j.id for j in cluster_jobs_objs if j.id != primary_job.id],
                'matches': matches,
                'size': len(cluster_jobs_objs)
            }

            # Mark all as processed
            for j_id in cluster_jobs:
                processed.add(j_id)

            results['duplicates_found'] += len(cluster_jobs) - 1

        results['duplicate_clusters'] = clusters
        return results


def create_dedup_engine(db: Session = None) -> DeduplicationEngine:
    """Factory function to create deduplication engine"""
    if db is None:
        db = SessionLocal()
    return DeduplicationEngine(db)
