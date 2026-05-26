"""
Batch scoring script for existing jobs.
This script runs the ranking engine on all existing jobs in the database.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime, timezone
from sqlalchemy import select, text
from app.database import SessionLocal
from app.models.job import Job

# Import ranking engine
from services.ranking import JobRankingEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
logger = logging.getLogger(__name__)


def batch_score_jobs(limit: int = None, dry_run: bool = False):
    """
    Run scoring on all existing jobs.
    
    Args:
        limit: Maximum number of jobs to process (None for all)
        dry_run: If True, don't actually save scores, just report
    """
    db = SessionLocal()
    
    try:
        # Get all active jobs that are not duplicates
        stmt = select(Job).where(Job.is_active == True, Job.is_duplicate == False)
        if limit:
            stmt = stmt.limit(limit)
        
        jobs = list(db.scalars(stmt).all())
        total_jobs = len(jobs)
        
        logger.info(f"Starting batch scoring for {total_jobs} jobs")
        
        ranking_engine = JobRankingEngine(db)
        
        jobs_processed = 0
        jobs_scored = 0
        total_score = 0
        min_score = 10.0
        max_score = 0.0
        
        for i, job in enumerate(jobs):
            if i % 100 == 0:
                logger.info(f"Processed {i}/{total_jobs} jobs ({i*100//total_jobs}%)")
            
            # Score the job
            scores = ranking_engine.score_job(job)
            
            jobs_scored += 1
            total_score += scores['final_score']
            min_score = min(min_score, scores['final_score'])
            max_score = max(max_score, scores['final_score'])
            
            if not dry_run:
                # Update job with scores
                job.final_score = scores['final_score']
                job.source_trust_score = scores['source_trust']
                job.freshness_score = scores['freshness']
                job.quality_score = scores['quality']
                job.company_score = scores['company']
                job.remote_authenticity = 'true-remote' if scores['remote_authenticity'] >= 9 else 'hybrid' if scores['remote_authenticity'] >= 5 else 'location-restricted'
                job.spam_indicator = 1.0 - (scores['quality'] / 10.0)  # Inverse quality
                
                # Also update job_scoring table if it exists
                try:
                    db.execute(
                        text("""
                        INSERT INTO job_scoring 
                        (job_id, source_trust_score, freshness_score, quality_score, 
                         company_score, remote_authenticity_score, salary_quality_score, 
                         final_score, scoring_version, calculated_at, updated_at)
                        VALUES 
                        (:job_id, :source_trust_score, :freshness_score, :quality_score,
                         :company_score, :remote_authenticity_score, :salary_quality_score,
                         :final_score, :scoring_version, :calculated_at, :updated_at)
                        ON CONFLICT(job_id) DO UPDATE SET
                        source_trust_score = excluded.source_trust_score,
                        freshness_score = excluded.freshness_score,
                        quality_score = excluded.quality_score,
                        company_score = excluded.company_score,
                        remote_authenticity_score = excluded.remote_authenticity_score,
                        salary_quality_score = excluded.salary_quality_score,
                        final_score = excluded.final_score,
                        scoring_version = excluded.scoring_version,
                        calculated_at = excluded.calculated_at,
                        updated_at = excluded.updated_at
                        """),
                        {
                            'job_id': job.id,
                            'source_trust_score': scores['source_trust'],
                            'freshness_score': scores['freshness'],
                            'quality_score': scores['quality'],
                            'company_score': scores['company'],
                            'remote_authenticity_score': scores['remote_authenticity'],
                            'salary_quality_score': scores['salary_quality'],
                            'final_score': scores['final_score'],
                            'scoring_version': 1,
                            'calculated_at': datetime.now(timezone.utc),
                            'updated_at': datetime.now(timezone.utc),
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to update job_scoring table: {e}")
            
            jobs_processed += 1
        
        if not dry_run:
            db.commit()
        
        avg_score = total_score / jobs_scored if jobs_scored > 0 else 0
        
        logger.info(f"Batch scoring complete:")
        logger.info(f"  Jobs processed: {jobs_processed}")
        logger.info(f"  Jobs scored: {jobs_scored}")
        logger.info(f"  Average score: {avg_score:.2f}")
        logger.info(f"  Min score: {min_score:.2f}")
        logger.info(f"  Max score: {max_score:.2f}")
        
        return {
            'jobs_processed': jobs_processed,
            'jobs_scored': jobs_scored,
            'avg_score': avg_score,
            'min_score': min_score,
            'max_score': max_score,
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error during batch scoring: {e}")
        raise
    finally:
        db.close()


def score_new_jobs(job_ids: list[int]):
    """
    Run scoring on specific job IDs (e.g., newly scraped jobs).
    
    Args:
        job_ids: List of job IDs to score
    """
    db = SessionLocal()
    
    try:
        jobs = list(db.scalars(select(Job).where(Job.id.in_(job_ids))).all())
        
        if not jobs:
            logger.info("No jobs to score")
            return
        
        logger.info(f"Scoring {len(jobs)} new jobs")
        
        ranking_engine = JobRankingEngine(db)
        
        for job in jobs:
            scores = ranking_engine.score_job(job)
            
            # Update job with scores
            job.final_score = scores['final_score']
            job.source_trust_score = scores['source_trust']
            job.freshness_score = scores['freshness']
            job.quality_score = scores['quality']
            job.company_score = scores['company']
            job.remote_authenticity = 'true-remote' if scores['remote_authenticity'] >= 9 else 'hybrid' if scores['remote_authenticity'] >= 5 else 'location-restricted'
            job.spam_indicator = 1.0 - (scores['quality'] / 10.0)
            
            # Update job_scoring table
            try:
                db.execute(
                    text("""
                    INSERT INTO job_scoring 
                    (job_id, source_trust_score, freshness_score, quality_score, 
                     company_score, remote_authenticity_score, salary_quality_score, 
                     final_score, scoring_version, calculated_at, updated_at)
                    VALUES 
                    (:job_id, :source_trust_score, :freshness_score, :quality_score,
                     :company_score, :remote_authenticity_score, :salary_quality_score,
                     :final_score, :scoring_version, :calculated_at, :updated_at)
                    ON CONFLICT(job_id) DO UPDATE SET
                    source_trust_score = excluded.source_trust_score,
                    freshness_score = excluded.freshness_score,
                    quality_score = excluded.quality_score,
                    company_score = excluded.company_score,
                    remote_authenticity_score = excluded.remote_authenticity_score,
                    salary_quality_score = excluded.salary_quality_score,
                    final_score = excluded.final_score,
                    scoring_version = excluded.scoring_version,
                    calculated_at = excluded.calculated_at,
                    updated_at = excluded.updated_at
                    """),
                    {
                        'job_id': job.id,
                        'source_trust_score': scores['source_trust'],
                        'freshness_score': scores['freshness'],
                        'quality_score': scores['quality'],
                        'company_score': scores['company'],
                        'remote_authenticity_score': scores['remote_authenticity'],
                        'salary_quality_score': scores['salary_quality'],
                        'final_score': scores['final_score'],
                        'scoring_version': 1,
                        'calculated_at': datetime.now(timezone.utc),
                        'updated_at': datetime.now(timezone.utc),
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to update job_scoring table: {e}")
        
        db.commit()
        logger.info(f"Scoring complete for {len(jobs)} jobs")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error during scoring: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch score jobs")
    parser.add_argument("--limit", type=int, help="Maximum number of jobs to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually save scores, just report")
    args = parser.parse_args()
    
    batch_score_jobs(limit=args.limit, dry_run=args.dry_run)
