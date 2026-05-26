"""
API endpoints for source health monitoring and performance dashboard.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.source_health import SourceHealthMonitor
from typing import List, Dict, Optional

router = APIRouter()


@router.get("/health/metrics")
async def get_quality_metrics(db: Session = Depends(get_db)) -> Dict:
    """
    Get overall quality metrics for the job database.
    """
    # Get job statistics
    result = db.execute("""
        SELECT 
            COUNT(*) as total_jobs,
            SUM(CASE WHEN is_duplicate = 1 THEN 1 ELSE 0 END) as duplicate_count,
            SUM(CASE WHEN spam_indicator > 0.5 THEN 1 ELSE 0 END) as spam_count,
            AVG(final_score) as avg_score
        FROM jobs
    """)
    job_stats = result.fetchone()
    
    # Get freshness metrics (jobs scraped in last 7 days)
    result = db.execute("""
        SELECT COUNT(*) as fresh_count
        FROM jobs
        WHERE scraped_at >= datetime('now', '-7 days')
    """)
    fresh_stats = result.fetchone()
    
    total_jobs = job_stats[0] if job_stats else 0
    duplicate_count = job_stats[1] if job_stats else 0
    spam_count = job_stats[2] if job_stats else 0
    avg_score = job_stats[3] if job_stats else 0
    fresh_count = fresh_stats[0] if fresh_stats else 0
    
    return {
        'total_jobs': total_jobs,
        'duplicate_count': duplicate_count,
        'duplicate_ratio': duplicate_count / total_jobs if total_jobs > 0 else 0,
        'spam_count': spam_count,
        'spam_ratio': spam_count / total_jobs if total_jobs > 0 else 0,
        'fresh_jobs': fresh_count,
        'freshness_ratio': fresh_count / total_jobs if total_jobs > 0 else 0,
        'avg_score': avg_score or 0,
    }


@router.get("/health/sources")
async def get_source_health(db: Session = Depends(get_db)) -> List[Dict]:
    """
    Get health status for all job sources.
    """
    monitor = SourceHealthMonitor(db)
    try:
        sources = monitor.get_all_sources_health()
        return sources
    finally:
        monitor.close()


@router.get("/health/sources/{source_name}")
async def get_source_health_detail(source_name: str, db: Session = Depends(get_db)) -> Optional[Dict]:
    """
    Get detailed health status for a specific source.
    """
    monitor = SourceHealthMonitor(db)
    try:
        health = monitor.get_source_health(source_name)
        return health
    finally:
        monitor.close()


@router.post("/health/sources/{source_name}/disable")
async def disable_source(source_name: str, reason: str = "", db: Session = Depends(get_db)) -> Dict:
    """
    Manually disable a source.
    """
    monitor = SourceHealthMonitor(db)
    try:
        monitor.disable_source(source_name, reason)
        return {'status': 'success', 'message': f'Source {source_name} disabled'}
    finally:
        monitor.close()


@router.post("/health/sources/{source_name}/enable")
async def enable_source(source_name: str, db: Session = Depends(get_db)) -> Dict:
    """
    Manually enable a source.
    """
    monitor = SourceHealthMonitor(db)
    try:
        monitor.enable_source(source_name)
        return {'status': 'success', 'message': f'Source {source_name} enabled'}
    finally:
        monitor.close()


@router.get("/health/summary")
async def get_health_summary(db: Session = Depends(get_db)) -> Dict:
    """
    Get summary metrics for all sources.
    """
    monitor = SourceHealthMonitor(db)
    try:
        summary = monitor.get_source_metrics_summary()
        return summary
    finally:
        monitor.close()


@router.get("/health/audit")
async def get_ingestion_audit(
    source_name: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
) -> List[Dict]:
    """
    Get ingestion audit trail.
    """
    query = """
        SELECT 
            source_name,
            run_id,
            jobs_fetched,
            jobs_new,
            jobs_duplicated,
            jobs_spam,
            jobs_stored,
            duration_seconds,
            error_message,
            status,
            started_at,
            completed_at
        FROM ingestion_audit
    """
    
    params = {}
    if source_name:
        query += " WHERE source_name = :source_name"
        params['source_name'] = source_name
    
    query += " ORDER BY started_at DESC LIMIT :limit"
    params['limit'] = limit
    
    result = db.execute(query, params)
    columns = result.keys()
    return [{col: row[i] for i, col in enumerate(columns)} for row in result.fetchall()]
