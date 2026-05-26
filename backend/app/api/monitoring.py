"""
API endpoints for monitoring and alerting.
"""

from fastapi import APIRouter, Depends
from typing import List, Optional
from app.services.monitoring import get_monitoring_service, Alert

router = APIRouter()


@router.get("/monitoring/metrics")
async def get_metrics():
    """
    Get current metrics summary.
    """
    monitoring = get_monitoring_service()
    monitoring.update_job_metrics()
    return monitoring.get_metrics_summary()


@router.get("/monitoring/alerts")
async def get_alerts(severity: Optional[str] = None):
    """
    Get active alerts, optionally filtered by severity.
    """
    monitoring = get_monitoring_service()
    alerts = monitoring.get_active_alerts(severity)
    return {
        'alerts': [
            {
                'severity': a.severity,
                'source': a.source,
                'message': a.message,
                'timestamp': a.timestamp.isoformat(),
                'metadata': a.metadata
            }
            for a in alerts
        ],
        'count': len(alerts)
    }


@router.post("/monitoring/alerts/clear")
async def clear_alerts(severity: Optional[str] = None):
    """
    Clear alerts, optionally by severity.
    """
    monitoring = get_monitoring_service()
    monitoring.clear_alerts(severity)
    return {'status': 'success', 'message': 'Alerts cleared'}


@router.post("/monitoring/health-check")
async def run_health_check():
    """
    Run a full system health check.
    """
    monitoring = get_monitoring_service()
    monitoring.check_source_health()
    monitoring.check_system_health()
    return {'status': 'success', 'message': 'Health check completed'}


@router.get("/monitoring/status")
async def get_system_status():
    """
    Get overall system status including health metrics.
    """
    monitoring = get_monitoring_service()
    monitoring.update_job_metrics()
    
    metrics = monitoring.get_metrics_summary()
    alerts = monitoring.get_active_alerts()
    
    # Determine overall status
    critical_alerts = [a for a in alerts if a.severity == 'critical']
    error_alerts = [a for a in alerts if a.severity == 'error']
    
    if critical_alerts:
        overall_status = 'critical'
    elif error_alerts:
        overall_status = 'degraded'
    else:
        overall_status = 'healthy'
    
    return {
        'status': overall_status,
        'metrics': metrics,
        'alert_count': len(alerts),
        'critical_alerts': len(critical_alerts),
        'error_alerts': len(error_alerts),
        'warning_alerts': len([a for a in alerts if a.severity == 'warning']),
    }
