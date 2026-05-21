"""Job bundles service for remote-ready job package bundles."""

import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_bundle import JobBundle


def create_default_job_bundles(db: Session) -> None:
    """
    Create default job bundles.
    This should be called once during setup.
    """
    default_bundles = [
        {
            "name": "DevOps Starter Kit",
            "description": "Everything you need to start your DevOps career",
            "category": "DevOps/Infrastructure",
            "price": 29.99,
            "currency": "USD",
            "is_free": False,
            "is_featured": True,
            "included_items": [
                {"type": "template", "name": "DevOps Resume Template"},
                {"type": "guide", "name": "DevOps Interview Prep Guide"},
                {"type": "checklist", "name": "DevOps Skills Checklist"},
                {"type": "resource", "name": "Tool Comparison Guide"},
            ],
        },
        {
            "name": "Full Stack Developer Bundle",
            "description": "Complete package for full stack development roles",
            "category": "Full Stack Development",
            "price": 39.99,
            "currency": "USD",
            "is_free": False,
            "is_featured": True,
            "included_items": [
                {"type": "template", "name": "Full Stack Resume Template"},
                {"type": "guide", "name": "Full Stack Portfolio Guide"},
                {"type": "checklist", "name": "Tech Stack Checklist"},
                {"type": "resource", "name": "Framework Comparison Guide"},
            ],
        },
        {
            "name": "Remote Job Seeker Free Kit",
            "description": "Free resources for remote job seekers",
            "category": "General",
            "price": 0,
            "currency": "USD",
            "is_free": True,
            "is_featured": True,
            "included_items": [
                {"type": "guide", "name": "Remote Job Search Guide"},
                {"type": "checklist", "name": "Remote Work Readiness Checklist"},
                {"type": "resource", "name": "Remote Companies List"},
            ],
        },
    ]
    
    for bundle_data in default_bundles:
        existing = db.scalar(
            select(JobBundle).where(JobBundle.name == bundle_data["name"])
        )
        
        if not existing:
            bundle = JobBundle(
                name=bundle_data["name"],
                description=bundle_data["description"],
                category=bundle_data["category"],
                price=bundle_data["price"],
                currency=bundle_data["currency"],
                is_free=bundle_data["is_free"],
                is_featured=bundle_data["is_featured"],
                included_items=json.dumps(bundle_data["included_items"]),
            )
            db.add(bundle)
    
    db.commit()


def list_job_bundles(
    db: Session,
    category: Optional[str] = None,
    featured_only: bool = False,
    free_only: bool = False,
) -> list[JobBundle]:
    """
    List job bundles with optional filters.
    """
    query = select(JobBundle).where(JobBundle.is_active == True)  # noqa: E712
    
    if category:
        query = query.where(JobBundle.category == category)
    if featured_only:
        query = query.where(JobBundle.is_featured == True)  # noqa: E712
    if free_only:
        query = query.where(JobBundle.is_free == True)  # noqa: E712
    
    query = query.order_by(JobBundle.is_featured.desc(), JobBundle.name)
    
    bundles = db.scalars(query).all()
    return list(bundles)


def get_job_bundle(db: Session, bundle_id: int) -> Optional[JobBundle]:
    """
    Get a specific job bundle by ID.
    """
    return db.get(JobBundle, bundle_id)


def get_featured_job_bundles(db: Session, limit: int = 5) -> list[JobBundle]:
    """
    Get featured job bundles.
    """
    bundles = db.scalars(
        select(JobBundle)
        .where(JobBundle.is_active == True, JobBundle.is_featured == True)  # noqa: E712
        .order_by(JobBundle.purchase_count.desc())
        .limit(limit)
    ).all()
    
    return list(bundles)


def increment_bundle_view(db: Session, bundle_id: int) -> Optional[JobBundle]:
    """
    Increment view count for a bundle.
    """
    bundle = get_job_bundle(db, bundle_id)
    if bundle:
        bundle.view_count += 1
        db.flush()
    return bundle


def increment_bundle_purchase(db: Session, bundle_id: int) -> Optional[JobBundle]:
    """
    Increment purchase count for a bundle.
    """
    bundle = get_job_bundle(db, bundle_id)
    if bundle:
        bundle.purchase_count += 1
        db.flush()
    return bundle
