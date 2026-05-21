"""Analytics API endpoints for premium features."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.analytics import (
    get_analytics_dashboard,
    get_job_market_heatmap,
    get_remote_hiring_trends,
    get_salary_insights,
    get_source_performance,
    update_source_performance_metrics,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
def analytics_dashboard(db: Session = Depends(get_db)):
    """
    Get comprehensive analytics dashboard data.
    Includes source performance, market heatmap, salary insights, and hiring trends.
    """
    return get_analytics_dashboard(db)


@router.get("/source-performance")
def source_performance(db: Session = Depends(get_db)):
    """
    Get performance metrics for all job sources.
    Shows which boards give the best matches.
    """
    return get_source_performance(db)


@router.get("/market-heatmap")
def market_heatmap(db: Session = Depends(get_db)):
    """
    Get job market heatmap data by region, role, and company size.
    Useful for visualizing job distribution.
    """
    return get_job_market_heatmap(db)


@router.get("/salary-insights")
def salary_insights(db: Session = Depends(get_db)):
    """
    Get salary and compensation insights.
    Breaks down salaries by seniority, region, and company size.
    """
    return get_salary_insights(db)


@router.get("/hiring-trends")
def hiring_trends(
    days: int = Query(30, ge=7, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
):
    """
    Get trends for remote hiring demand over time.
    Shows growth rates and daily job counts.
    """
    return get_remote_hiring_trends(db, days=days)


@router.post("/update-metrics")
def update_metrics(db: Session = Depends(get_db)):
    """
    Update source performance metrics in the database.
    This should be called periodically to keep metrics fresh.
    """
    update_source_performance_metrics(db)
    return {"status": "success", "message": "Metrics updated successfully"}
