"""Company profiles and employer ratings service."""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.job import Job


def get_or_create_company(db: Session, company_name: str) -> Company:
    """
    Get existing company or create a new one.
    """
    company = db.scalar(
        select(Company).where(Company.name == company_name)
    )
    
    if not company:
        company = Company(name=company_name)
        db.add(company)
        db.flush()
    
    return company


def update_company_from_job(db: Session, company_name: str, job_data: dict) -> Company:
    """
    Update company profile based on job data.
    Infers company size, industry, etc. from job listings.
    """
    company = get_or_create_company(db, company_name)
    
    # Update company size if not set
    if not company.company_size and job_data.get("company_size"):
        company.company_size = job_data["company_size"]
    
    # Mark as remote-friendly if we see remote jobs
    if job_data.get("is_verified_remote"):
        company.is_remote_friendly = True
    
    return company


def get_company_jobs(db: Session, company_name: str, limit: int = 20) -> list[Job]:
    """
    Get all jobs for a specific company.
    """
    jobs = db.scalars(
        select(Job)
        .where(Job.company == company_name, Job.is_active == True)  # noqa: E712
        .order_by(Job.posted_at.desc().nullslast())
        .limit(limit)
    ).all()
    
    return list(jobs)


def get_company_stats(db: Session, company_name: str) -> dict:
    """
    Get statistics for a specific company.
    """
    jobs = list(db.scalars(
        select(Job).where(Job.company == company_name, Job.is_active == True)  # noqa: E712
    ))
    
    if not jobs:
        return {
            "company": company_name,
            "total_jobs": 0,
            "verified_remote_jobs": 0,
            "by_seniority": {},
            "by_tech_stack": {},
        }
    
    verified_count = sum(1 for job in jobs if job.is_verified_remote)
    
    # Count by seniority
    seniority_counts = {}
    for job in jobs:
        seniority = job.seniority_tag or "Unknown"
        seniority_counts[seniority] = seniority_counts.get(seniority, 0) + 1
    
    # Count by tech stack
    tech_counts = {}
    for job in jobs:
        for tech in (job.tech_stack or "").split(","):
            tech = tech.strip()
            if tech:
                tech_counts[tech] = tech_counts.get(tech, 0) + 1
    
    return {
        "company": company_name,
        "total_jobs": len(jobs),
        "verified_remote_jobs": verified_count,
        "verified_remote_percentage": round(verified_count / len(jobs) * 100, 2) if jobs else 0,
        "by_seniority": seniority_counts,
        "by_tech_stack": dict(sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
    }


def list_all_companies(db: Session, limit: int = 100) -> list[Company]:
    """
    List all companies with job listings.
    """
    companies = db.scalars(
        select(Company)
        .order_by(Company.name)
        .limit(limit)
    ).all()
    
    return list(companies)


def search_companies(db: Session, query: str, limit: int = 20) -> list[Company]:
    """
    Search companies by name.
    """
    companies = db.scalars(
        select(Company)
        .where(Company.name.ilike(f"%{query}%"))
        .order_by(Company.name)
        .limit(limit)
    ).all()
    
    return list(companies)
