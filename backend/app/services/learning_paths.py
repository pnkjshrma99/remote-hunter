"""Learning paths service for recommended learning paths per job role."""

import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.job_profiles import list_all_profiles
from app.models.learning_path import LearningPath


def create_default_learning_paths(db: Session) -> None:
    """
    Create default learning paths for all job profiles.
    This should be called once during setup.
    """
    profiles = list_all_profiles()
    
    for profile in profiles:
        existing = db.scalar(
            select(LearningPath).where(LearningPath.job_profile_id == profile.id)
        )
        
        if not existing:
            # Generate learning path based on profile
            modules = generate_learning_modules(profile)
            resources = generate_learning_resources(profile)
            
            learning_path = LearningPath(
                job_profile_id=profile.id,
                title=f"{profile.name} Learning Path",
                description=f"Comprehensive learning path to become a {profile.name}",
                difficulty_level="beginner" if profile.min_experience < 2 else "intermediate",
                estimated_weeks=profile.min_experience * 4 if profile.min_experience else 12,
                modules=json.dumps(modules),
                resources=json.dumps(resources),
                is_active=True,
                is_featured=True,
            )
            db.add(learning_path)
    
    db.commit()


def generate_learning_modules(profile) -> list[dict]:
    """
    Generate learning modules based on job profile.
    """
    base_modules = [
        {
            "title": "Foundations",
            "description": "Core concepts and fundamentals",
            "weeks": 2,
            "topics": ["Computer Science Basics", "Git & Version Control", "Terminal/CLI"],
        },
        {
            "title": "Core Skills",
            "description": "Essential skills for the role",
            "weeks": 4,
            "topics": profile.keywords[:5] if profile.keywords else [],
        },
        {
            "title": "Advanced Topics",
            "description": "Advanced concepts and best practices",
            "weeks": 4,
            "topics": ["System Design", "Testing", "CI/CD", "Security"],
        },
        {
            "title": "Projects",
            "description": "Hands-on portfolio projects",
            "weeks": 4,
            "topics": ["Portfolio Project 1", "Portfolio Project 2", "Open Source Contribution"],
        },
    ]
    
    return base_modules


def generate_learning_resources(profile) -> list[dict]:
    """
    Generate learning resources based on job profile.
    """
    base_resources = [
        {
            "type": "course",
            "title": "Official Documentation",
            "url": "#",
            "free": True,
        },
        {
            "type": "book",
            "title": "Industry Standard Books",
            "url": "#",
            "free": False,
        },
        {
            "type": "practice",
            "title": "Coding Challenges",
            "url": "#",
            "free": True,
        },
    ]
    
    return base_resources


def get_learning_path(db: Session, job_profile_id: str) -> Optional[LearningPath]:
    """
    Get learning path for a specific job profile.
    """
    return db.scalar(
        select(LearningPath).where(
            LearningPath.job_profile_id == job_profile_id,
            LearningPath.is_active == True  # noqa: E712
        )
    )


def list_learning_paths(db: Session) -> list[LearningPath]:
    """
    List all active learning paths.
    """
    paths = db.scalars(
        select(LearningPath)
        .where(LearningPath.is_active == True)  # noqa: E712
        .order_by(LearningPath.is_featured.desc(), LearningPath.title)
    ).all()
    
    return list(paths)


def get_featured_learning_paths(db: Session, limit: int = 5) -> list[LearningPath]:
    """
    Get featured learning paths.
    """
    paths = db.scalars(
        select(LearningPath)
        .where(LearningPath.is_active == True, LearningPath.is_featured == True)  # noqa: E712
        .order_by(LearningPath.title)
        .limit(limit)
    ).all()
    
    return list(paths)
