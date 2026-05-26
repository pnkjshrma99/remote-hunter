"""
Monitoring and Alerting Service

Provides metrics collection, health checks, and alerting for the Remote Hunter system.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict

from prometheus_client import Counter, Histogram, Gauge, start_http_server
from sqlalchemy import text
from app.database import SessionLocal
from app.services.source_health import SourceHealthMonitor, IngestionResult

logger = logging.getLogger(__name__)


# Prometheus Metrics
# Counters
SCRAPE_REQUESTS_TOTAL = Counter('scrape_requests_total', 'Total scrape requests', ['status'])
JOBS_INGESTED_TOTAL = Counter('jobs_ingested_total', 'Total jobs ingested', ['source'])
DUPLICATES_DETECTED_TOTAL = Counter('duplicates_detected_total', 'Total duplicates detected')
SPAM_JOBS_TOTAL = Counter('spam_jobs_total', 'Total spam jobs detected')

# Histograms
SCRAPE_DURATION = Histogram('scrape_duration_seconds', 'Scrape duration in seconds')
JOB_PROCESSING_DURATION = Histogram('job_processing_duration_seconds', 'Job processing duration')

# Gauges
ACTIVE_SOURCES = Gauge('active_sources_count', 'Number of active job sources')
TOTAL_JOBS = Gauge('total_jobs_count', 'Total number of jobs in database')
DUPLICATE_RATIO = Gauge('duplicate_ratio', 'Ratio of duplicate jobs')
AVG_JOB_SCORE = Gauge('avg_job_score', 'Average job score')


@dataclass
class Alert:
    """Represents an alert"""
    severity: str  # 'info', 'warning', 'error', 'critical'
    source: str
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict = field(default_factory=dict)


class MonitoringService:
    """Main monitoring and alerting service"""
    
    def __init__(self, metrics_port: int = 9090):
        self.metrics_port = metrics_port
        self.alerts: List[Alert] = []
        self.alert_history: List[Alert] = []
        self.max_alert_history = 1000
        self._metrics_server_started = False
    
    def start_metrics_server(self):
        """Start Prometheus metrics server"""
        if not self._metrics_server_started:
            try:
                start_http_server(self.metrics_port)
                self._metrics_server_started = True
                logger.info(f"Prometheus metrics server started on port {self.metrics_port}")
            except Exception as e:
                logger.error(f"Failed to start metrics server: {e}")
    
    def record_scrape_request(self, status: str, duration: float):
        """Record a scrape request"""
        SCRAPE_REQUESTS_TOTAL.labels(status=status).inc()
        SCRAPE_DURATION.observe(duration)
    
    def record_jobs_ingested(self, source: str, count: int):
        """Record jobs ingested from a source"""
        JOBS_INGESTED_TOTAL.labels(source=source).inc(count)
    
    def record_duplicate_detected(self, count: int = 1):
        """Record duplicate detection"""
        DUPLICATES_DETECTED_TOTAL.inc(count)
    
    def record_spam_job(self, count: int = 1):
        """Record spam job detection"""
        SPAM_JOBS_TOTAL.inc(count)
    
    def update_job_metrics(self):
        """Update job-related metrics from database"""
        db = SessionLocal()
        try:
            # Total jobs
            result = db.execute(text("SELECT COUNT(*) FROM jobs WHERE is_active = 1"))
            total = result.scalar()
            TOTAL_JOBS.set(total)
            
            # Duplicate ratio
            result = db.execute(text("""
                SELECT 
                    CAST(SUM(CASE WHEN is_duplicate = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) 
                FROM jobs WHERE is_active = 1
            """))
            dup_ratio = result.scalar() or 0
            DUPLICATE_RATIO.set(dup_ratio)
            
            # Average job score
            result = db.execute(text("SELECT AVG(final_score) FROM jobs WHERE is_active = 1 AND final_score > 0"))
            avg_score = result.scalar() or 0
            AVG_JOB_SCORE.set(avg_score)
            
            # Active sources
            result = db.execute(text("SELECT COUNT(*) FROM source_metadata WHERE is_active = 1"))
            active_sources = result.scalar()
            ACTIVE_SOURCES.set(active_sources)
            
        except Exception as e:
            logger.error(f"Error updating job metrics: {e}")
        finally:
            db.close()
    
    def create_alert(self, severity: str, source: str, message: str, metadata: Dict = None):
        """Create and store an alert"""
        alert = Alert(
            severity=severity,
            source=source,
            message=message,
            metadata=metadata or {}
        )
        
        self.alerts.append(alert)
        self.alert_history.append(alert)
        
        # Trim history
        if len(self.alert_history) > self.max_alert_history:
            self.alert_history = self.alert_history[-self.max_alert_history:]
        
        # Log alert
        log_level = {
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }.get(severity, logging.INFO)
        
        logger.log(log_level, f"[{severity.upper()}] {source}: {message}")
        
        # Send critical alerts immediately
        if severity in ['error', 'critical']:
            self._send_alert(alert)
    
    def _send_alert(self, alert: Alert):
        """Send alert to configured channels"""
        # This would integrate with email, Slack, etc.
        # For now, just log it
        logger.critical(f"ALERT: {alert.source} - {alert.message}")
    
    def get_active_alerts(self, severity: Optional[str] = None) -> List[Alert]:
        """Get active alerts, optionally filtered by severity"""
        if severity:
            return [a for a in self.alerts if a.severity == severity]
        return self.alerts
    
    def clear_alerts(self, severity: Optional[str] = None):
        """Clear alerts, optionally by severity"""
        if severity:
            self.alerts = [a for a in self.alerts if a.severity != severity]
        else:
            self.alerts = []
    
    def check_source_health(self):
        """Check health of all sources and create alerts if needed"""
        db = SessionLocal()
        try:
            monitor = SourceHealthMonitor(db)
            sources = monitor.get_all_sources_health()
            
            for source in sources:
                # Check for unhealthy sources
                if source.get('health_status') == 'unhealthy':
                    self.create_alert(
                        severity='error',
                        source=source['source_name'],
                        message=f"Source is unhealthy: {source['consecutive_failures']} consecutive failures",
                        metadata={'consecutive_failures': source['consecutive_failures']}
                    )
                elif source.get('health_status') == 'degraded':
                    self.create_alert(
                        severity='warning',
                        source=source['source_name'],
                        message=f"Source is degraded: {source['consecutive_failures']} consecutive failures",
                        metadata={'consecutive_failures': source['consecutive_failures']}
                    )
                
                # Check for high duplicate ratio
                dup_ratio = source.get('duplicate_ratio', 0)
                if dup_ratio > 0.5:
                    self.create_alert(
                        severity='warning',
                        source=source['source_name'],
                        message=f"High duplicate ratio: {dup_ratio:.2%}",
                        metadata={'duplicate_ratio': dup_ratio}
                    )
            
        except Exception as e:
            logger.error(f"Error checking source health: {e}")
        finally:
            db.close()
    
    def check_system_health(self):
        """Overall system health check"""
        db = SessionLocal()
        try:
            # Check database connectivity
            result = db.execute(text("SELECT 1"))
            if not result.scalar():
                self.create_alert(
                    severity='critical',
                    source='database',
                    message='Database connectivity check failed'
                )
            
            # Check for stale jobs (no new jobs in 7 days)
            result = db.execute(text("""
                SELECT COUNT(*) FROM jobs 
                WHERE scraped_at >= datetime('now', '-7 days')
            """))
            fresh_jobs = result.scalar()
            
            if fresh_jobs == 0:
                self.create_alert(
                    severity='warning',
                    source='system',
                    message='No fresh jobs in the last 7 days',
                    metadata={'fresh_jobs': fresh_jobs}
                )
            
            # Check for high spam ratio
            result = db.execute(text("""
                SELECT 
                    CAST(SUM(CASE WHEN spam_indicator > 0.5 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) 
                FROM jobs WHERE is_active = 1
            """))
            spam_ratio = result.scalar() or 0
            
            if spam_ratio > 0.3:
                self.create_alert(
                    severity='warning',
                    source='system',
                    message=f'High spam ratio: {spam_ratio:.2%}',
                    metadata={'spam_ratio': spam_ratio}
                )
            
        except Exception as e:
            self.create_alert(
                severity='critical',
                source='system',
                message=f'System health check failed: {str(e)}'
            )
        finally:
            db.close()
    
    def get_metrics_summary(self) -> Dict:
        """Get summary of all metrics"""
        db = SessionLocal()
        try:
            summary = {
                'total_jobs': TOTAL_JOBS._value.get(),
                'active_sources': ACTIVE_SOURCES._value.get(),
                'duplicate_ratio': DUPLICATE_RATIO._value.get(),
                'avg_job_score': AVG_JOB_SCORE._value.get(),
                'active_alerts': len(self.alerts),
                'alert_breakdown': defaultdict(int)
            }
            
            for alert in self.alerts:
                summary['alert_breakdown'][alert.severity] += 1
            
            return summary
        finally:
            db.close()


# Global monitoring service instance
_monitoring_service = None


def get_monitoring_service(metrics_port: int = 9090) -> MonitoringService:
    """Get or create global monitoring service"""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService(metrics_port=metrics_port)
    return _monitoring_service
