"""Premium Analytics service for job market insights."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.analytics import JobAnalytics, SourcePerformance
from app.models.job import Job
from app.services.quality_trust import extract_salary_range


def get_source_performance(db: Session) -> list[dict[str, Any]]:
    """
    Get performance metrics for all job sources.
    Returns list of source performance data.
    """
    jobs = list(db.scalars(select(Job).where(Job.is_active == True)))  # noqa: E712
    
    source_stats = defaultdict(lambda: {
        "total_scraped": 0,
        "total_matched": 0,
        "verified_remote_count": 0,
        "duplicate_count": 0,
        "salary_count": 0,
    })
    
    for job in jobs:
        stats = source_stats[job.source]
        stats["total_scraped"] += 1
        stats["total_matched"] += 1  # All active jobs are considered matched
        if getattr(job, "is_verified_remote", False):
            stats["verified_remote_count"] += 1
        if getattr(job, "is_duplicate", False):
            stats["duplicate_count"] += 1
        if job.salary:
            stats["salary_count"] += 1
    
    # Calculate rates
    performance_data = []
    for source, stats in source_stats.items():
        total = stats["total_scraped"]
        match_rate = (stats["total_matched"] / total * 100) if total > 0 else 0
        duplicate_rate = (stats["duplicate_count"] / total * 100) if total > 0 else 0
        verified_rate = (stats["verified_remote_count"] / total * 100) if total > 0 else 0
        
        performance_data.append({
            "source": source,
            "total_scraped": total,
            "total_matched": stats["total_matched"],
            "match_rate": round(match_rate, 2),
            "duplicate_rate": round(duplicate_rate, 2),
            "verified_remote_rate": round(verified_rate, 2),
            "salary_data_available": stats["salary_count"],
        })
    
    # Sort by total scraped descending
    performance_data.sort(key=lambda x: x["total_scraped"], reverse=True)
    
    return performance_data


def get_job_market_heatmap(db: Session) -> dict[str, Any]:
    """
    Get job market heatmap data by region, role, and company size.
    Returns structured data for heatmap visualization.
    """
    jobs = list(db.scalars(select(Job).where(Job.is_active == True)))  # noqa: E712
    
    # Region breakdown
    region_counts: Counter[str] = Counter()
    for job in jobs:
        region = job.region_eligibility or "Unknown"
        region_counts[region] += 1
    
    # Role category breakdown (from seniority_tag)
    role_counts: Counter[str] = Counter()
    for job in jobs:
        role = getattr(job, "seniority_tag", None) or "Unknown"
        role_counts[role] += 1
    
    # Company size breakdown
    size_counts: Counter[str] = Counter()
    for job in jobs:
        size = job.company_size or "Unknown"
        size_counts[size] += 1
    
    # Tech stack breakdown
    tech_counts: Counter[str] = Counter()
    for job in jobs:
        for tech in (job.tech_stack or "").split(","):
            tech = tech.strip()
            if tech:
                tech_counts[tech] += 1
    
    return {
        "by_region": dict(region_counts.most_common()),
        "by_role": dict(role_counts.most_common()),
        "by_company_size": dict(size_counts.most_common()),
        "by_tech_stack": dict(tech_counts.most_common(20)),
        "total_jobs": len(jobs),
    }


def get_salary_insights(db: Session) -> dict[str, Any]:
    """
    Get salary and compensation insights.
    Returns salary ranges by role, region, and experience level.
    """
    jobs = list(db.scalars(select(Job).where(Job.is_active == True, Job.salary.isnot(None))))  # noqa: E712
    
    salary_data = []
    for job in jobs:
        min_sal, max_sal = extract_salary_range(job.salary or "")
        if min_sal or max_sal:
            salary_data.append({
                "min_salary": min_sal,
                "max_salary": max_sal,
                "seniority": getattr(job, "seniority_tag", None) or "Unknown",
                "region": job.region_eligibility or "Unknown",
                "company_size": job.company_size or "Unknown",
            })
    
    # Calculate averages by category
    by_seniority = defaultdict(list)
    by_region = defaultdict(list)
    by_company_size = defaultdict(list)
    
    for data in salary_data:
        avg_salary = (data["min_salary"] + data["max_salary"]) / 2 if data["min_salary"] and data["max_salary"] else (data["min_salary"] or data["max_salary"])
        if avg_salary:
            if data["seniority"]:
                by_seniority[data["seniority"]].append(avg_salary)
            if data["region"]:
                by_region[data["region"]].append(avg_salary)
            if data["company_size"]:
                by_company_size[data["company_size"]].append(avg_salary)
    
    def calculate_avg(salaries: list[float]) -> Optional[float]:
        return round(sum(salaries) / len(salaries), 2) if salaries else None
    
    return {
        "total_with_salary": len(salary_data),
        "by_seniority": {
            k: calculate_avg(v) for k, v in by_seniority.items()
        },
        "by_region": {
            k: calculate_avg(v) for k, v in by_region.items()
        },
        "by_company_size": {
            k: calculate_avg(v) for k, v in by_company_size.items()
        },
        "overall_average": calculate_avg([
            (d["min_salary"] + d["max_salary"]) / 2 
            for d in salary_data 
            if d["min_salary"] and d["max_salary"]
        ]),
    }


def get_remote_hiring_trends(db: Session, days: int = 30) -> dict[str, Any]:
    """
    Get trends for remote hiring demand over time.
    Returns daily/weekly job counts and growth rates.
    """
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    jobs = list(db.scalars(
        select(Job).where(Job.is_active == True)  # noqa: E712
    ))
    
    # Group by date
    daily_counts: defaultdict[str, int] = defaultdict(int)
    daily_verified: defaultdict[str, int] = defaultdict(int)
    daily_by_seniority: defaultdict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
    
    for job in jobs:
        date_source = job.posted_at or job.scraped_at
        if date_source and date_source >= cutoff:
            date_str = date_source.date().isoformat()
            daily_counts[date_str] += 1
            if getattr(job, "is_verified_remote", False):
                daily_verified[date_str] += 1
            seniority = getattr(job, "seniority_tag", None)
            if seniority:
                daily_by_seniority[date_str][seniority] += 1
    
    # Fill in missing dates
    date_range = [
        (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=i)).date().isoformat()
        for i in reversed(range(days))
    ]
    
    trend_data = []
    for date_str in date_range:
        trend_data.append({
            "date": date_str,
            "total_jobs": daily_counts.get(date_str, 0),
            "verified_remote": daily_verified.get(date_str, 0),
            "by_seniority": dict(daily_by_seniority.get(date_str, {})),
        })
    
    # Calculate growth rates
    if len(trend_data) >= 2:
        first_week_avg = sum(d["total_jobs"] for d in trend_data[:7]) / 7
        last_week_avg = sum(d["total_jobs"] for d in trend_data[-7:]) / 7
        growth_rate = ((last_week_avg - first_week_avg) / first_week_avg * 100) if first_week_avg > 0 else 0
    else:
        growth_rate = 0
    
    return {
        "period_days": days,
        "trend_data": trend_data,
        "growth_rate_percent": round(growth_rate, 2),
        "total_jobs_in_period": len(jobs),
    }


def get_analytics_dashboard(db: Session) -> dict[str, Any]:
    """
    Get comprehensive analytics dashboard data.
    Combines all analytics into a single response.
    """
    return {
        "source_performance": get_source_performance(db),
        "market_heatmap": get_job_market_heatmap(db),
        "salary_insights": get_salary_insights(db),
        "hiring_trends": get_remote_hiring_trends(db, days=30),
        "generated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
    }


def update_source_performance_metrics(db: Session) -> None:
    """
    Update source performance metrics in the database.
    This should be called periodically to keep metrics fresh.
    """
    performance_data = get_source_performance(db)
    
    for data in performance_data:
        existing = db.scalar(
            select(SourcePerformance).where(SourcePerformance.source == data["source"])
        )
        
        if existing:
            existing.total_scraped = data["total_scraped"]
            existing.total_matched = data["total_matched"]
            existing.match_rate = data["match_rate"]
            existing.duplicate_rate = data["duplicate_rate"]
            existing.avg_relevance_score = data.get("verified_remote_rate", 0)
            existing.last_scraped_at = datetime.utcnow()
        else:
            perf = SourcePerformance(
                source=data["source"],
                total_scraped=data["total_scraped"],
                total_matched=data["total_matched"],
                match_rate=data["match_rate"],
                duplicate_rate=data["duplicate_rate"],
                avg_relevance_score=data.get("verified_remote_rate", 0),
                last_scraped_at=datetime.utcnow(),
            )
            db.add(perf)
    
    db.commit()
