"""Intelligent Job Scoring & Ranking Engine

Multi-dimensional scoring system that ranks jobs based on:
- Source trust & reliability
- Freshness (recency decay)
- Quality indicators
- Company legitimacy
- Remote authenticity
- Salary transparency
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import math

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.job import Job
from app.database import SessionLocal

logger = logging.getLogger(__name__)

# Scoring weights (must sum to 1.0)
SCORING_WEIGHTS = {
    'source_trust': 0.20,
    'freshness': 0.25,
    'quality': 0.20,
    'company': 0.15,
    'remote_authenticity': 0.10,
    'salary_quality': 0.10,
}

# Source trust scores
SOURCE_TRUST_SCORES = {
    # High-trust direct ATS
    'greenhouse': 10.0,
    'lever': 10.0,
    'ashby': 10.0,
    'workable': 10.0,

    # Premium job boards
    'wellfound': 9.0,
    'indie_hackers': 9.5,
    'yc_jobs': 9.0,

    # Quality developer boards
    'github_jobs': 9.0,
    'devto_jobs': 9.0,
    'authentic_jobs': 8.5,
    'product_hunt': 8.0,

    # Established boards
    'weworkremotely': 7.5,
    'remotive': 6.5,
    'arbeitnow': 6.0,
    'stackoverflow': 7.0,
    'hashnode': 7.5,

    # Lower-quality RSS feeds
    'remoteok': 5.0,
    'working_nomads': 4.5,
    'himalayas': 4.0,
    'jobicy': 4.0,
    'jobspresso': 4.5,

    # Default/unknown
    'unknown': 3.0,
}


class FreshnessScorer:
    """Calculates freshness score with time decay"""

    # Configuration
    FRESH_THRESHOLD_HOURS = 24  # Jobs <24h are "fresh"
    RECENT_THRESHOLD_DAYS = 3   # Jobs <3d are "recent"
    DECAY_HALF_LIFE_DAYS = 7    # Score halves every 7 days

    @classmethod
    def score(cls, posted_at: datetime, now: datetime = None) -> float:
        """
        Calculate freshness score (0-10).

        Score decay function:
        - <24h: 10.0 (maximum)
        - <3 days: 8.0-10.0
        - <7 days: 6.0-8.0
        - <14 days: 4.0-6.0
        - >30 days: <2.0 (very stale)

        Uses exponential decay: score = 10 * exp(-days / half_life)
        """
        if not posted_at:
            return 5.0  # Unknown posts get median score

        if now is None:
            now = datetime.utcnow()

        age_seconds = (now - posted_at).total_seconds()
        age_days = age_seconds / (24 * 3600)

        # Clamp negative ages
        if age_days < 0:
            age_days = 0

        # Exponential decay function
        # S(t) = 10 * exp(-t / half_life)
        decay_factor = age_days / cls.DECAY_HALF_LIFE_DAYS
        score = 10.0 * math.exp(-decay_factor)

        # Clamp to 0-10
        return min(10.0, max(0.0, score))


class QualityScorer:
    """Calculates job quality score based on content indicators"""

    @classmethod
    def score(cls, job: Job) -> float:
        """Calculate quality score (0-10) based on job attributes"""
        score = 5.0  # Base score

        # 1. Description quality & completeness
        if job.description:
            desc_length = len(job.description)

            # Bonus for detailed descriptions
            if desc_length > 1000:
                score += 2.0
            elif desc_length > 500:
                score += 1.5
            elif desc_length > 200:
                score += 1.0

            # Penalty for very short descriptions
            if desc_length < 100:
                score -= 2.0

        else:
            score -= 3.0  # Heavy penalty for no description

        # 2. Salary transparency
        if job.salary and job.salary.strip():
            # Check if salary contains numbers (range or amount)
            has_salary_amount = any(c.isdigit() for c in job.salary)

            if has_salary_amount:
                score += 1.5

                # Extra bonus if contains range (e.g., "$100k-$150k")
                if '-' in job.salary and has_salary_amount:
                    score += 0.5

        else:
            score -= 1.0

        # 3. Company information completeness
        if job.company and len(job.company) > 3:
            score += 0.5

        # 4. Location clarity
        if job.location and job.location.lower() != 'remote':
            score += 0.5
        elif not job.location or job.location.strip() == '':
            score -= 1.0

        # 5. URL validity (is it resolvable?)
        if job.url:
            # Check for reasonable URL format
            if job.url.startswith(('http://', 'https://')) and '.' in job.url:
                score += 0.5
            else:
                score -= 1.0

        # 6. Detect spam indicators
        spam_score = cls._detect_spam_indicators(job)
        score -= (spam_score * 2.0)  # Negative impact

        # Clamp to 0-10
        return min(10.0, max(0.0, score))

    @classmethod
    def _detect_spam_indicators(cls, job: Job) -> float:
        """Detect spam indicators (0-1, where 1 = very spammy)"""
        spam_score = 0.0

        combined_text = f"{job.title} {job.company} {job.description or ''}"

        # 1. Excessive emojis
        emoji_count = sum(1 for c in combined_text if ord(c) > 127)
        if emoji_count > 5:
            spam_score += 0.3

        # 2. Suspicious patterns
        suspicious_patterns = [
            'bitcoin', 'crypto', 'forex', 'mlm', 'pyramid',
            'guarantee', 'guaranteed', 'no experience needed',
            'work from anywhere instantly'
        ]
        for pattern in suspicious_patterns:
            if pattern.lower() in combined_text.lower():
                spam_score += 0.2

        # 3. Unrealistic salary claims
        if job.salary:
            try:
                # Extract numbers from salary
                import re
                numbers = re.findall(r'\d+', job.salary)
                if numbers:
                    salary_amount = int(numbers[0])

                    # If claiming >$1M/year, likely spam
                    if salary_amount > 1000000:
                        spam_score += 0.4

                    # If claiming <$1/hour, likely spam
                    if salary_amount < 1 and 'hour' in job.salary.lower():
                        spam_score += 0.3
            except:
                pass

        # 4. Poor grammar/spelling (basic check)
        if job.title and len(job.title.split()) > 0:
            words_with_caps = sum(1 for w in job.title.split() if w.isupper())
            if words_with_caps > len(job.title.split()) * 0.5:
                spam_score += 0.2

        return min(1.0, spam_score)


class CompanyScorer:
    """Calculates company legitimacy & trust score"""

    @classmethod
    def score(cls, job: Job, company_info: Optional[Dict] = None) -> float:
        """Calculate company score (0-10)"""
        score = 5.0  # Base score

        # 1. Domain-based signals
        if job.url and cls._is_company_domain(job.url):
            score += 2.0

        # 2. Company name length (very short names are suspicious)
        if job.company:
            if len(job.company) < 3:
                score -= 2.0
            elif len(job.company) > 100:
                score -= 1.0  # Suspiciously long
            else:
                score += 0.5  # Normal length

        # 3. If company_info provided (from enrichment)
        if company_info:
            if company_info.get('has_website'):
                score += 1.0

            if company_info.get('has_linkedin'):
                score += 1.5

            if company_info.get('is_startup'):
                score += 0.5

            if company_info.get('domain_authority', 0) > 50:
                score += 1.0
            elif company_info.get('domain_authority', 0) > 30:
                score += 0.5

        # Clamp to 0-10
        return min(10.0, max(0.0, score))

    @staticmethod
    def _is_company_domain(url: str) -> bool:
        """Check if URL is a company domain (not a job board)"""
        job_board_domains = {
            'linkedin.com', 'indeed.com', 'glassdoor.com',
            'remotive.com', 'remoteok.io', 'weworkremotely.com',
            'github.com/jobs', 'dev.to', 'angel.co', 'wellfound.com'
        }

        return not any(domain in url.lower() for domain in job_board_domains)


class RemoteAuthenticityScorer:
    """Detects if a job is truly remote vs. hybrid disguised"""

    @classmethod
    def score(cls, job: Job) -> float:
        """Calculate remote authenticity score (0-10)"""

        if not job.location:
            return 8.0  # Uncertain, give high score

        location_lower = job.location.lower()

        # True remote: no location specified or explicit
        if any(phrase in location_lower for phrase in [
            'remote', 'distributed', 'anywhere', 'global'
        ]):
            # Check for restrictions
            if any(phrase in location_lower for phrase in [
                'timezone', 'utc', 'est', 'pst', 'hours', 'overlap'
            ]):
                return 7.0  # Timezone-restricted remote

            return 10.0  # True remote, no restrictions

        # Hybrid or location-based
        if any(phrase in location_lower for phrase in [
            'hybrid', 'office', 'onsite', 'new york',
            'san francisco', 'london', 'california'
        ]):
            return 2.0  # Not remote

        # Ambiguous location
        if any(phrase in location_lower for phrase in [
            'usa', 'us', 'uk', 'europe', 'canada'
        ]):
            return 5.0  # Possibly remote with location preference

        # Unknown
        return 5.0


class SalaryQualityScorer:
    """Scores salary information quality & transparency"""

    @classmethod
    def score(cls, job: Job) -> float:
        """Calculate salary quality score (0-10)"""
        score = 3.0  # Base for unknown salary

        if not job.salary:
            return score

        salary_lower = job.salary.lower().strip()

        # Has range (e.g., "$100k - $150k")
        if '-' in salary_lower:
            score = 9.0
            return min(10.0, score)

        # Has specific amount
        if any(c.isdigit() for c in salary_lower):
            score = 7.0

            # Has currency indicator
            if any(curr in salary_lower for curr in ['$', '€', '£', 'usd', 'eur', 'gbp']):
                score = 8.0

            # Has period (per year, monthly, hourly)
            if any(period in salary_lower for period in ['year', 'month', 'hour', 'week', 'annual']):
                score = 9.0

        return min(10.0, score)


class JobRankingEngine:
    """Main ranking engine combining all scoring dimensions"""

    def __init__(self, db: Session):
        self.db = db

    def score_job(self, job: Job, company_info: Optional[Dict] = None) -> Dict[str, float]:
        """
        Calculate all scoring components for a job.

        Returns dict with:
        {
            'source_trust': 0-10,
            'freshness': 0-10,
            'quality': 0-10,
            'company': 0-10,
            'remote_authenticity': 0-10,
            'salary_quality': 0-10,
            'final_score': 0-10,
            'percentile': 0-100
        }
        """
        scores = {
            'source_trust': self._get_source_trust(job.source),
            'freshness': FreshnessScorer.score(job.posted_at),
            'quality': QualityScorer.score(job),
            'company': CompanyScorer.score(job, company_info),
            'remote_authenticity': RemoteAuthenticityScorer.score(job),
            'salary_quality': SalaryQualityScorer.score(job),
        }

        # Calculate final composite score
        scores['final_score'] = self._calculate_final_score(scores)
        scores['percentile'] = None  # Will be calculated after ranking all jobs

        return scores

    def _get_source_trust(self, source: str) -> float:
        """Get trust score for source"""
        return SOURCE_TRUST_SCORES.get(source.lower(), SOURCE_TRUST_SCORES['unknown'])

    @staticmethod
    def _calculate_final_score(scores: Dict[str, float]) -> float:
        """Calculate weighted composite score"""
        final_score = sum(
            scores[component] * SCORING_WEIGHTS.get(component, 0)
            for component in SCORING_WEIGHTS.keys()
            if component in scores
        )
        return min(10.0, max(0.0, final_score))

    def rank_jobs(self, jobs: List[Job], company_info_map: Optional[Dict[int, Dict]] = None) -> List[Tuple[Job, Dict]]:
        """
        Rank list of jobs by computed score.

        Returns list of (job, scores) tuples sorted by final_score DESC
        """
        if company_info_map is None:
            company_info_map = {}

        # Score all jobs
        scored_jobs = []
        for job in jobs:
            scores = self.score_job(job, company_info_map.get(job.id))
            scored_jobs.append((job, scores))

        # Sort by final score descending
        scored_jobs.sort(key=lambda x: x[1]['final_score'], reverse=True)

        # Calculate percentiles
        total = len(scored_jobs)
        for idx, (job, scores) in enumerate(scored_jobs):
            percentile = ((total - idx) / total) * 100
            scores['percentile'] = percentile

        return scored_jobs

    def batch_score_jobs(self, job_ids: List[int], save_to_db: bool = True) -> Dict:
        """
        Score a batch of jobs and optionally save to database.

        Returns statistics about the scoring run.
        """
        jobs = self.db.query(Job).filter(Job.id.in_(job_ids)).all()

        if not jobs:
            return {'jobs_processed': 0, 'jobs_scored': 0}

        ranked = self.rank_jobs(jobs)

        if save_to_db:
            # Update jobs in database
            for job, scores in ranked:
                job.final_score = scores['final_score']
                job.source_trust_score = scores['source_trust']
                job.freshness_score = scores['freshness']
                job.quality_score = scores['quality']
                job.company_score = scores['company']
                job.remote_authenticity = 'true-remote' if scores['remote_authenticity'] >= 9 else 'hybrid' if scores['remote_authenticity'] >= 5 else 'location-restricted'
                job.spam_indicator = 1.0 - (scores['quality'] / 10.0)  # Inverse quality

            self.db.commit()

        return {
            'jobs_processed': len(jobs),
            'jobs_scored': len(ranked),
            'avg_score': sum(scores['final_score'] for _, scores in ranked) / len(ranked),
            'min_score': min(scores['final_score'] for _, scores in ranked),
            'max_score': max(scores['final_score'] for _, scores in ranked),
        }


def create_ranking_engine(db: Session = None) -> JobRankingEngine:
    """Factory function to create ranking engine"""
    if db is None:
        db = SessionLocal()
    return JobRankingEngine(db)
