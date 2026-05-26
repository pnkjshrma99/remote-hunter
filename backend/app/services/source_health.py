"""
Source health monitoring service.
Tracks source performance, failure rates, and automatically disables unhealthy sources.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from sqlalchemy import text
from app.database import SessionLocal

logger = logging.getLogger(__name__)


class IngestionResult:
    """Data class for ingestion results."""
    def __init__(
        self,
        source_name: str,
        status: str,
        jobs_fetched: int = 0,
        jobs_new: int = 0,
        jobs_duplicated: int = 0,
        jobs_spam: int = 0,
        jobs_stored: int = 0,
        duration_seconds: int = 0,
        error_message: Optional[str] = None,
    ):
        self.source_name = source_name
        self.status = status  # 'success', 'partial', 'failed'
        self.jobs_fetched = jobs_fetched
        self.jobs_new = jobs_new
        self.jobs_duplicated = jobs_duplicated
        self.jobs_spam = jobs_spam
        self.jobs_stored = jobs_stored
        self.duration_seconds = duration_seconds
        self.error_message = error_message


class SourceHealthMonitor:
    """Monitor and track health of job sources."""
    
    def __init__(self, db=None):
        self.db = db or SessionLocal()
    
    def update_source_health(self, result: IngestionResult) -> Dict:
        """
        Update source metrics after ingestion.
        
        Args:
            result: IngestionResult from a scrape run
            
        Returns:
            Updated source metadata
        """
        try:
            # Get or create source metadata
            metadata = self._get_or_create_source_metadata(result.source_name)
            
            if result.status == 'success':
                # Success: update success metrics
                metadata['last_successful_run'] = datetime.utcnow()
                metadata['failure_count'] = 0
                metadata['consecutive_failures'] = 0
                metadata['successful_ingestions'] = (metadata.get('successful_ingestions', 0) or 0) + 1
                metadata['total_jobs_ingested'] = (metadata.get('total_jobs_ingested', 0) or 0) + result.jobs_stored
                
                # Calculate duplicate ratio
                if result.jobs_fetched > 0:
                    duplicate_ratio = result.jobs_duplicated / result.jobs_fetched
                    metadata['duplicate_ratio'] = duplicate_ratio
                
                # Re-enable if was disabled
                if not metadata.get('is_active', True):
                    metadata['is_active'] = True
                    logger.info(f"Re-enabled source: {result.source_name}")
                    
            elif result.status == 'partial':
                # Partial success: still count as success but log warning
                metadata['last_successful_run'] = datetime.utcnow()
                metadata['failure_count'] = 0
                metadata['consecutive_failures'] = 0
                metadata['successful_ingestions'] = (metadata.get('successful_ingestions', 0) or 0) + 1
                metadata['total_jobs_ingested'] = (metadata.get('total_jobs_ingested', 0) or 0) + result.jobs_stored
                
                logger.warning(f"Partial success for source {result.source_name}: {result.error_message}")
                
            else:  # failed
                # Failure: increment failure counters
                metadata['last_failed_run'] = datetime.utcnow()
                metadata['failure_count'] = (metadata.get('failure_count', 0) or 0) + 1
                metadata['consecutive_failures'] = (metadata.get('consecutive_failures', 0) or 0) + 1
                
                # Auto-disable if too many consecutive failures
                if metadata['consecutive_failures'] >= 5:
                    metadata['is_active'] = False
                    logger.warning(f"Disabled source: {result.source_name} (too many failures: {metadata['consecutive_failures']})")
            
            # Update timestamp
            metadata['updated_at'] = datetime.utcnow()
            
            # Save to database
            self._save_source_metadata(result.source_name, metadata)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error updating source health for {result.source_name}: {e}")
            raise
    
    def _get_or_create_source_metadata(self, source_name: str) -> Dict:
        """Get existing source metadata or create default."""
        result = self.db.execute(
            text("SELECT * FROM source_metadata WHERE source_name = :source_name"),
            {'source_name': source_name}
        )
        row = result.fetchone()
        
        if row:
            # Convert to dict
            columns = result.keys()
            return {col: row[i] for i, col in enumerate(columns)}
        else:
            # Create default metadata
            return {
                'source_name': source_name,
                'trust_score': 5.0,
                'spam_score': 0.0,
                'freshness_score': 5.0,
                'duplicate_ratio': 0.0,
                'is_active': True,
                'last_successful_run': None,
                'last_failed_run': None,
                'failure_count': 0,
                'consecutive_failures': 0,
                'total_jobs_ingested': 0,
                'successful_ingestions': 0,
                'source_type': 'unknown',
                'api_endpoint': None,
                'rate_limit_per_hour': None,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
            }
    
    def _save_source_metadata(self, source_name: str, metadata: Dict):
        """Save source metadata to database."""
        self.db.execute(
            text("""
                INSERT INTO source_metadata 
                (source_name, trust_score, spam_score, freshness_score, duplicate_ratio,
                 is_active, last_successful_run, last_failed_run, failure_count,
                 consecutive_failures, total_jobs_ingested, successful_ingestions,
                 source_type, api_endpoint, rate_limit_per_hour, created_at, updated_at)
                VALUES 
                (:source_name, :trust_score, :spam_score, :freshness_score, :duplicate_ratio,
                 :is_active, :last_successful_run, :last_failed_run, :failure_count,
                 :consecutive_failures, :total_jobs_ingested, :successful_ingestions,
                 :source_type, :api_endpoint, :rate_limit_per_hour, :created_at, :updated_at)
                ON CONFLICT(source_name) DO UPDATE SET
                trust_score = excluded.trust_score,
                spam_score = excluded.spam_score,
                freshness_score = excluded.freshness_score,
                duplicate_ratio = excluded.duplicate_ratio,
                is_active = excluded.is_active,
                last_successful_run = excluded.last_successful_run,
                last_failed_run = excluded.last_failed_run,
                failure_count = excluded.failure_count,
                consecutive_failures = excluded.consecutive_failures,
                total_jobs_ingested = excluded.total_jobs_ingested,
                successful_ingestions = excluded.successful_ingestions,
                source_type = excluded.source_type,
                api_endpoint = excluded.api_endpoint,
                rate_limit_per_hour = excluded.rate_limit_per_hour,
                updated_at = excluded.updated_at
            """),
            metadata
        )
        self.db.commit()
    
    def get_source_health(self, source_name: str) -> Optional[Dict]:
        """Get health status for a specific source."""
        result = self.db.execute(
            text("SELECT * FROM source_metadata WHERE source_name = :source_name"),
            {'source_name': source_name}
        )
        row = result.fetchone()
        
        if not row:
            return None
        
        columns = result.keys()
        metadata = {col: row[i] for i, col in enumerate(columns)}
        
        # Calculate health status
        failure_count = metadata.get('failure_count', 0) or 0
        consecutive_failures = metadata.get('consecutive_failures', 0) or 0
        
        if consecutive_failures >= 5:
            health_status = 'unhealthy'
        elif consecutive_failures >= 2:
            health_status = 'degraded'
        else:
            health_status = 'healthy'
        
        metadata['health_status'] = health_status
        return metadata
    
    def get_all_sources_health(self) -> list:
        """Get health status for all sources."""
        result = self.db.execute(
            text("""
                SELECT 
                    source_name,
                    trust_score,
                    is_active,
                    last_successful_run,
                    last_failed_run,
                    failure_count,
                    consecutive_failures,
                    total_jobs_ingested,
                    successful_ingestions,
                    duplicate_ratio,
                    CASE 
                        WHEN consecutive_failures >= 5 THEN 'unhealthy'
                        WHEN consecutive_failures >= 2 THEN 'degraded'
                        ELSE 'healthy'
                    END as health_status
                FROM source_metadata
                ORDER BY trust_score DESC
            """)
        )
        
        columns = result.keys()
        return [{col: row[i] for i, col in enumerate(columns)} for row in result.fetchall()]
    
    def disable_source(self, source_name: str, reason: str = ""):
        """Manually disable a source."""
        self.db.execute(
            text("""
                UPDATE source_metadata 
                SET is_active = 0, updated_at = :updated_at
                WHERE source_name = :source_name
            """),
            {'source_name': source_name, 'updated_at': datetime.utcnow()}
        )
        self.db.commit()
        logger.info(f"Manually disabled source: {source_name} (reason: {reason})")
    
    def enable_source(self, source_name: str):
        """Manually enable a source."""
        self.db.execute(
            text("""
                UPDATE source_metadata 
                SET is_active = 1, consecutive_failures = 0, updated_at = :updated_at
                WHERE source_name = :source_name
            """),
            {'source_name': source_name, 'updated_at': datetime.utcnow()}
        )
        self.db.commit()
        logger.info(f"Manually enabled source: {source_name}")
    
    def log_ingestion_audit(self, result: IngestionResult, run_id: str = None):
        """Log ingestion run to audit trail."""
        import uuid
        
        if not run_id:
            run_id = str(uuid.uuid4())
        
        self.db.execute(
            text("""
                INSERT INTO ingestion_audit 
                (source_name, run_id, jobs_fetched, jobs_new, jobs_duplicated, 
                 jobs_spam, jobs_stored, duration_seconds, error_message, status, 
                 started_at, completed_at)
                VALUES 
                (:source_name, :run_id, :jobs_fetched, :jobs_new, :jobs_duplicated,
                 :jobs_spam, :jobs_stored, :duration_seconds, :error_message, :status,
                 :started_at, :completed_at)
            """),
            {
                'source_name': result.source_name,
                'run_id': run_id,
                'jobs_fetched': result.jobs_fetched,
                'jobs_new': result.jobs_new,
                'jobs_duplicated': result.jobs_duplicated,
                'jobs_spam': result.jobs_spam,
                'jobs_stored': result.jobs_stored,
                'duration_seconds': result.duration_seconds,
                'error_message': result.error_message,
                'status': result.status,
                'started_at': datetime.utcnow() - timedelta(seconds=result.duration_seconds),
                'completed_at': datetime.utcnow(),
            }
        )
        self.db.commit()
    
    def get_source_metrics_summary(self) -> Dict:
        """Get summary metrics for all sources."""
        result = self.db.execute(
            text("""
                SELECT 
                    COUNT(*) as total_sources,
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_sources,
                    SUM(CASE WHEN consecutive_failures >= 5 THEN 1 ELSE 0 END) as unhealthy_sources,
                    SUM(total_jobs_ingested) as total_jobs_ingested,
                    AVG(trust_score) as avg_trust_score,
                    AVG(duplicate_ratio) as avg_duplicate_ratio
                FROM source_metadata
            """)
        )
        
        row = result.fetchone()
        columns = result.keys()
        return {col: row[i] for i, col in enumerate(columns)}
    
    def close(self):
        """Close database connection."""
        if self.db:
            self.db.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
