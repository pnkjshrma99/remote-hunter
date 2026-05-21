"""Job profile configurations for remote job search."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class JobProfile:
    """A predefined job profile with keywords and search criteria."""
    id: str
    name: str
    keywords: List[str]
    description: str
    min_experience: int
    max_experience: int
    role_category: str


# Predefined job profiles for easy selection
JOB_PROFILES: Dict[str, JobProfile] = {
    "devops-junior": JobProfile(
        id="devops-junior",
        name="DevOps Engineer (Junior)",
        keywords=["devops", "sre", "site reliability", "platform engineer", "infrastructure"],
        description="Junior DevOps/SRE roles focusing on cloud operations and infrastructure",
        min_experience=0,
        max_experience=2,
        role_category="DevOps/Infrastructure",
    ),
    "devops-mid": JobProfile(
        id="devops-mid",
        name="DevOps Engineer (Mid-Level)",
        keywords=["devops", "sre", "platform engineer", "infrastructure engineer", "cloud ops"],
        description="Mid-level DevOps/SRE roles with some professional experience",
        min_experience=2,
        max_experience=5,
        role_category="DevOps/Infrastructure",
    ),
    "fullstack-junior": JobProfile(
        id="fullstack-junior",
        name="Full Stack Developer (Junior)",
        keywords=["full stack", "fullstack", "react", "node", "python", "javascript"],
        description="Junior full stack developer roles across web technologies",
        min_experience=0,
        max_experience=2,
        role_category="Full Stack Development",
    ),
    "fullstack-mid": JobProfile(
        id="fullstack-mid",
        name="Full Stack Developer (Mid-Level)",
        keywords=["full stack", "fullstack", "react", "vue", "node", "python", "backend"],
        description="Mid-level full stack developer positions",
        min_experience=2,
        max_experience=5,
        role_category="Full Stack Development",
    ),
    "backend-junior": JobProfile(
        id="backend-junior",
        name="Backend Engineer (Junior)",
        keywords=["backend", "api", "python", "java", "go", "node"],
        description="Junior backend engineer roles in various programming languages",
        min_experience=0,
        max_experience=2,
        role_category="Backend Development",
    ),
    "backend-mid": JobProfile(
        id="backend-mid",
        name="Backend Engineer (Mid-Level)",
        keywords=["backend", "api", "microservices", "python", "java", "go"],
        description="Mid-level backend engineer positions",
        min_experience=2,
        max_experience=5,
        role_category="Backend Development",
    ),
    "frontend-junior": JobProfile(
        id="frontend-junior",
        name="Frontend Developer (Junior)",
        keywords=["frontend", "react", "vue", "angular", "javascript", "typescript", "css"],
        description="Junior frontend developer roles",
        min_experience=0,
        max_experience=2,
        role_category="Frontend Development",
    ),
    "frontend-mid": JobProfile(
        id="frontend-mid",
        name="Frontend Developer (Mid-Level)",
        keywords=["frontend", "react", "vue", "angular", "javascript", "typescript"],
        description="Mid-level frontend developer positions",
        min_experience=2,
        max_experience=5,
        role_category="Frontend Development",
    ),
    "cloud-engineer": JobProfile(
        id="cloud-engineer",
        name="Cloud Engineer",
        keywords=["cloud", "aws", "gcp", "azure", "infrastructure", "devops"],
        description="Cloud infrastructure and platform engineering roles",
        min_experience=1,
        max_experience=5,
        role_category="Cloud/Infrastructure",
    ),
    "ml-engineer": JobProfile(
        id="ml-engineer",
        name="Machine Learning Engineer",
        keywords=["machine learning", "ml", "python", "tensorflow", "pytorch", "data science"],
        description="Machine learning and AI engineering roles",
        min_experience=1,
        max_experience=5,
        role_category="Machine Learning",
    ),
    "data-engineer": JobProfile(
        id="data-engineer",
        name="Data Engineer",
        keywords=["data engineer", "etl", "pipeline", "sql", "python", "spark"],
        description="Data engineering and ETL roles",
        min_experience=1,
        max_experience=5,
        role_category="Data Engineering",
    ),
    "security-engineer": JobProfile(
        id="security-engineer",
        name="Security Engineer",
        keywords=["security", "infosec", "devops", "cloud", "kubernetes"],
        description="Security and compliance engineering roles",
        min_experience=2,
        max_experience=7,
        role_category="Security",
    ),
    "qa-engineer": JobProfile(
        id="qa-engineer",
        name="QA Engineer",
        keywords=["qa", "test", "automation", "selenium", "python", "javascript"],
        description="Quality assurance and test automation roles",
        min_experience=0,
        max_experience=4,
        role_category="Quality Assurance",
    ),
}


def get_profile_by_id(profile_id: str) -> Optional[JobProfile]:
    """Get a job profile by ID."""
    return JOB_PROFILES.get(profile_id)


def list_all_profiles() -> List[JobProfile]:
    """List all available job profiles."""
    return list(JOB_PROFILES.values())


def list_profiles_by_category(category: str) -> List[JobProfile]:
    """List all profiles in a given category."""
    return [p for p in JOB_PROFILES.values() if p.role_category == category]


def get_all_categories() -> List[str]:
    """Get all available job categories."""
    return sorted(list(set(p.role_category for p in JOB_PROFILES.values())))
