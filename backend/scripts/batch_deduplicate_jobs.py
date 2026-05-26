"""
Batch deduplication script for existing jobs.
This script runs the deduplication engine on all existing jobs in the database.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime, timezone
from sqlalchemy import select, text
from app.database import SessionLocal
from app.models.job import Job

# Import deduplication engine
from services.deduplication import DeduplicationEngine, JobNormalizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
logger = logging.getLogger(__name__)


def batch_deduplicate_jobs(limit: int = None, dry_run: bool = False):
    """
    Run deduplication on all existing jobs.
    
    Args:
        limit: Maximum number of jobs to process (None for all)
        dry_run: If True, don't actually mark duplicates, just report
    """
    db = SessionLocal()
    
    try:
        # Get all active jobs that are not already marked as duplicates
        stmt = select(Job).where(Job.is_active == True, Job.is_duplicate == False)
        if limit:
            stmt = stmt.limit(limit)
        
        jobs = list(db.scalars(stmt).all())
        total_jobs = len(jobs)
        
        logger.info(f"Starting batch deduplication for {total_jobs} jobs")
        
        dedup_engine = DeduplicationEngine(db)
        normalizer = JobNormalizer()
        
        duplicates_found = 0
        clusters_created = 0
        jobs_processed = 0
        
        for i, job in enumerate(jobs):
            if i % 100 == 0:
                logger.info(f"Processed {i}/{total_jobs} jobs ({i*100//total_jobs}%)")
            
            # Find duplicates for this job
            matches = dedup_engine.find_duplicates_for_job(job)
            
            if matches:
                duplicates_found += len(matches)
                
                # Create cluster
                cluster_hash = normalizer.normalize_title(job.title) + "|" + normalizer.normalize_company(job.company)
                cluster_hash = cluster_hash.replace(" ", "_")
                
                if not dry_run:
                    # Create duplicate cluster
                    db.execute(
                        text("""
                            INSERT INTO duplicate_clusters 
                            (primary_job_id, cluster_hash, duplicate_count, match_type, created_at, updated_at)
                            VALUES (:primary_job_id, :cluster_hash, :duplicate_count, :match_type, :created_at, :updated_at)
                            ON CONFLICT(cluster_hash) DO UPDATE SET
                            duplicate_count = duplicate_count + 1,
                            updated_at = :updated_at
                        """),
                        {
                            'primary_job_id': job.id,
                            'cluster_hash': cluster_hash,
                            'duplicate_count': len(matches) + 1,
                            'match_type': matches[0].match_type,
                            'created_at': datetime.now(timezone.utc),
                            'updated_at': datetime.now(timezone.utc),
                        }
                    )
                    
                    # Get cluster ID
                    result = db.execute(
                        text("SELECT id FROM duplicate_clusters WHERE cluster_hash = :cluster_hash"),
                        {'cluster_hash': cluster_hash}
                    )
                    cluster_id = result.scalar()
                    
                    # Mark matched jobs as duplicates
                    for match in matches:
                        db.execute(
                            text("""
                                INSERT INTO duplicate_members 
                                (cluster_id, job_id, similarity_score, match_type, created_at)
                                VALUES (:cluster_id, :job_id, :similarity_score, :match_type, :created_at)
                                ON CONFLICT(cluster_id, job_id) DO NOTHING
                            """),
                            {
                                'cluster_id': cluster_id,
                                'job_id': match.matched_with,
                                'similarity_score': match.similarity_score,
                                'match_type': match.match_type,
                                'created_at': datetime.now(timezone.utc),
                            }
                        )
                        
                        # Mark job as duplicate
                        db.execute(
                            text("UPDATE jobs SET is_duplicate = 1, duplicate_group_id = :cluster_id WHERE id = :job_id"),
                            {'cluster_id': cluster_id, 'job_id': match.matched_with}
                        )
                    
                    clusters_created += 1
                else:
                    logger.info(f"DRY RUN: Would mark {len(matches)} duplicates for job {job.id} ({job.title} at {job.company})")
            
            jobs_processed += 1
        
        if not dry_run:
            db.commit()
        
        logger.info(f"Batch deduplication complete:")
        logger.info(f"  Jobs processed: {jobs_processed}")
        logger.info(f"  Duplicates found: {duplicates_found}")
        logger.info(f"  Clusters created: {clusters_created}")
        
        return {
            'jobs_processed': jobs_processed,
            'duplicates_found': duplicates_found,
            'clusters_created': clusters_created,
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error during batch deduplication: {e}")
        raise
    finally:
        db.close()


def deduplicate_new_jobs(job_ids: list[int]):
    """
    Run deduplication on specific job IDs (e.g., newly scraped jobs).
    
    Args:
        job_ids: List of job IDs to deduplicate
    """
    db = SessionLocal()
    
    try:
        jobs = list(db.scalars(select(Job).where(Job.id.in_(job_ids))).all())
        
        if not jobs:
            logger.info("No jobs to deduplicate")
            return
        
        logger.info(f"Deduplicating {len(jobs)} new jobs")
        
        dedup_engine = DeduplicationEngine(db)
        normalizer = JobNormalizer()
        
        duplicates_found = 0
        
        for job in jobs:
            matches = dedup_engine.find_duplicates_for_job(job)
            
            if matches:
                duplicates_found += len(matches)
                
                # Create cluster
                cluster_hash = normalizer.normalize_title(job.title) + "|" + normalizer.normalize_company(job.company)
                cluster_hash = cluster_hash.replace(" ", "_")
                
                # Create duplicate cluster
                db.execute(
                    text("""
                        INSERT INTO duplicate_clusters 
                        (primary_job_id, cluster_hash, duplicate_count, match_type, created_at, updated_at)
                        VALUES (:primary_job_id, :cluster_hash, :duplicate_count, :match_type, :created_at, :updated_at)
                        ON CONFLICT(cluster_hash) DO UPDATE SET
                        duplicate_count = duplicate_count + 1,
                        updated_at = :updated_at
                    """),
                    {
                        'primary_job_id': job.id,
                        'cluster_hash': cluster_hash,
                        'duplicate_count': len(matches) + 1,
                        'match_type': matches[0].match_type,
                        'created_at': datetime.now(timezone.utc),
                        'updated_at': datetime.now(timezone.utc),
                    }
                )
                
                # Get cluster ID
                result = db.execute(
                    text("SELECT id FROM duplicate_clusters WHERE cluster_hash = :cluster_hash"),
                    {'cluster_hash': cluster_hash}
                )
                cluster_id = result.scalar()
                
                # Mark matched jobs as duplicates
                for match in matches:
                    db.execute(
                        text("""
                            INSERT INTO duplicate_members 
                            (cluster_id, job_id, similarity_score, match_type, created_at)
                            VALUES (:cluster_id, :job_id, :similarity_score, :match_type, :created_at)
                            ON CONFLICT(cluster_id, job_id) DO NOTHING
                        """),
                        {
                            'cluster_id': cluster_id,
                            'job_id': match.matched_with,
                            'similarity_score': match.similarity_score,
                            'match_type': match.match_type,
                            'created_at': datetime.now(timezone.utc),
                        }
                    )
                    
                    # Mark job as duplicate
                    db.execute(
                        text("UPDATE jobs SET is_duplicate = 1, duplicate_group_id = :cluster_id WHERE id = :job_id"),
                        {'cluster_id': cluster_id, 'job_id': match.matched_with}
                    )
        
        db.commit()
        logger.info(f"Deduplication complete: {duplicates_found} duplicates found")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error during deduplication: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch deduplicate jobs")
    parser.add_argument("--limit", type=int, help="Maximum number of jobs to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually mark duplicates, just report")
    args = parser.parse_args()
    
    batch_deduplicate_jobs(limit=args.limit, dry_run=args.dry_run)
