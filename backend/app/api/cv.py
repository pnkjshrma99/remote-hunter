"""CV upload and management API endpoints."""

import os
import shutil
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session
import PyPDF2
from docx import Document

from app.database import get_db
from app.models.cv import CV, CVJobMatch
from app.models.user import User
from app.models.job import Job
from app.services.cv_parser import CVParser
from app.services.jobs import run_scrape
from app.services.cloudinary_service import upload_bytes_to_cloudinary, delete_file_from_cloudinary
from app.schemas.job import ScrapeRequest
from app.api.auth import get_current_user

router = APIRouter(prefix="/cv", tags=["cv"])

# Upload directory for CVs (fallback for local storage)
UPLOAD_DIR = "uploads/cvs"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class CVUpdateRequest(BaseModel):
    skills: Optional[list[str]] = Field(default=None)
    tech_stack: Optional[list[str]] = Field(default=None)
    job_roles: Optional[list[str]] = Field(default=None)
    keywords: Optional[list[str]] = Field(default=None)
    experience_years: Optional[int] = Field(default=None, ge=0, le=80)


def clean_string_list(values: Optional[list[str]]) -> Optional[list[str]]:
    if values is None:
        return None

    cleaned = []
    seen = set()
    for value in values:
        item = str(value).strip()
        key = item.lower()
        if item and key not in seen:
            cleaned.append(item)
            seen.add(key)
    return cleaned


def calculate_ats_analysis(cv: CV) -> dict:
    tech_count = len(cv.tech_stack or [])
    skill_count = len(cv.skills or [])
    role_count = len(cv.job_roles or [])
    keyword_count = len(cv.keywords or [])
    education_count = len(cv.education or [])
    certification_count = len(cv.certifications or [])

    sections_score = min(20, (tech_count > 0) * 5 + (role_count > 0) * 4 + (cv.experience_years is not None) * 4 + (education_count > 0) * 4 + (keyword_count > 0) * 3)
    skills_score = min(25, tech_count * 2 + skill_count)
    experience_score = 0
    if cv.experience_years is not None:
        experience_score = 10 if cv.experience_years <= 2 else 15 if cv.experience_years <= 5 else 20
    role_score = min(15, role_count * 5)
    keyword_score = min(15, keyword_count)
    credential_score = min(5, education_count * 3 + certification_count * 2)

    score = sections_score + skills_score + experience_score + role_score + keyword_score + credential_score
    score = max(0, min(int(score), 100))

    recommendations = []
    if tech_count < 8:
        recommendations.append("Add more concrete tools, frameworks, languages, and platforms from your recent work.")
    if role_count == 0:
        recommendations.append("Add a clear target role such as backend developer, data engineer, or DevOps engineer.")
    if cv.experience_years is None:
        recommendations.append("Add total years of professional experience in a simple ATS-readable format.")
    if keyword_count < 8:
        recommendations.append("Add measurable project keywords from job descriptions you are targeting.")
    if education_count == 0 and certification_count == 0:
        recommendations.append("Add education or relevant certifications if they apply.")
    if not recommendations:
        recommendations.append("Your CV has strong ATS coverage. Tune keywords for each job description before applying.")

    return {
        "score": score,
        "rating": "Strong" if score >= 80 else "Good" if score >= 60 else "Needs work",
        "breakdown": [
            {"label": "ATS-readable sections", "score": sections_score, "max_score": 20},
            {"label": "Skills and tech depth", "score": skills_score, "max_score": 25},
            {"label": "Experience clarity", "score": experience_score, "max_score": 20},
            {"label": "Target role alignment", "score": role_score, "max_score": 15},
            {"label": "Keyword coverage", "score": keyword_score, "max_score": 15},
            {"label": "Education and certifications", "score": credential_score, "max_score": 5},
        ],
        "signals": {
            "tech_stack": tech_count,
            "skills": skill_count,
            "job_roles": role_count,
            "keywords": keyword_count,
            "experience_years": cv.experience_years,
            "education": education_count,
            "certifications": certification_count,
        },
        "recommendations": recommendations,
    }


def sync_ats_score(cv: CV) -> dict:
    analysis = calculate_ats_analysis(cv)
    cv.ats_score = analysis["score"]
    parsed_data = dict(cv.parsed_data or {})
    parsed_data["ats_analysis"] = analysis
    cv.parsed_data = parsed_data
    return analysis


@router.post("/upload")
async def upload_cv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and parse a CV file."""
    
    # Validate file type
    allowed_extensions = {'.pdf', '.docx', '.doc', '.txt'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Read file content
    file_content = await file.read()
    file_size = len(file_content)
    
    # Upload to Cloudinary
    cloudinary_url, upload_result = upload_bytes_to_cloudinary(
        file_bytes=file_content,
        filename=file.filename,
        folder=f"cvs/user_{current_user.id}",
        resource_type="raw"
    )
    
    if not cloudinary_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file to Cloudinary"
        )
    
    # Extract text from file content
    try:
        if file_ext == '.txt':
            text = file_content.decode('utf-8')
        elif file_ext == '.pdf':
            import io
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        elif file_ext in ['.docx', '.doc']:
            import io
            doc = Document(io.BytesIO(file_content))
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        else:
            text = ""
    except Exception as e:
        # If text extraction fails, still save the CV but with empty text
        text = ""
    
    # Parse CV
    parsed_data = CVParser.parse_cv(text)
    
    # Create CV record
    cv = CV(
        user_id=current_user.id,
        cloudinary_url=cloudinary_url,
        file_name=file.filename,
        file_size=file_size,
        content_type=file.content_type,
        parsed_data=parsed_data,
        skills=parsed_data['skills'],
        tech_stack=parsed_data['tech_stack'],
        job_roles=parsed_data.get('job_roles', []),
        keywords=parsed_data.get('keywords', []),
        experience_years=parsed_data['experience_years'],
        education=parsed_data['education'],
        certifications=parsed_data['certifications'],
        created_at=datetime.utcnow()
    )
    sync_ats_score(cv)
    
    db.add(cv)
    db.commit()
    db.refresh(cv)
    
    return {
        "id": cv.id,
        "file_name": cv.file_name,
        "skills": cv.skills,
        "tech_stack": cv.tech_stack,
        "job_roles": cv.job_roles,
        "keywords": cv.keywords,
        "experience_years": cv.experience_years,
        "message": "CV uploaded and parsed successfully"
    }


@router.get("/my-cvs")
async def get_my_cvs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all CVs for the current user."""
    cvs = db.query(CV).filter(CV.user_id == current_user.id).order_by(CV.created_at.desc()).all()
    ats_changed = False
    for cv in cvs:
        if cv.ats_score is None:
            sync_ats_score(cv)
            ats_changed = True
    if ats_changed:
        db.commit()
    match_counts = dict(
        db.query(CVJobMatch.cv_id, func.count(CVJobMatch.id))
        .filter(CVJobMatch.cv_id.in_([cv.id for cv in cvs]))
        .group_by(CVJobMatch.cv_id)
        .all()
    ) if cvs else {}
    average_match_scores = dict(
        db.query(CVJobMatch.cv_id, func.avg(CVJobMatch.match_score))
        .filter(CVJobMatch.cv_id.in_([cv.id for cv in cvs]))
        .group_by(CVJobMatch.cv_id)
        .all()
    ) if cvs else {}
    
    return [
        {
            "id": cv.id,
            "file_name": cv.file_name,
            "skills": cv.skills,
            "tech_stack": cv.tech_stack,
            "job_roles": cv.job_roles,
            "keywords": cv.keywords,
            "experience_years": cv.experience_years,
            "created_at": cv.created_at.isoformat(),
            "ats_score": cv.ats_score,
            "matched_jobs_count": match_counts.get(cv.id, 0),
            "match_rate": round(float(average_match_scores.get(cv.id, 0) or 0))
        }
        for cv in cvs
    ]


@router.get("/{cv_id}")
async def get_cv(
    cv_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific CV by ID."""
    cv = db.query(CV).filter(
        CV.id == cv_id,
        CV.user_id == current_user.id
    ).first()
    
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )
    
    ats_analysis = sync_ats_score(cv)
    db.commit()
    db.refresh(cv)
    
    return {
        "id": cv.id,
        "file_name": cv.file_name,
        "skills": cv.skills,
        "tech_stack": cv.tech_stack,
        "job_roles": cv.job_roles,
        "keywords": cv.keywords,
        "experience_years": cv.experience_years,
        "education": cv.education,
        "certifications": cv.certifications,
        "parsed_data": cv.parsed_data,
        "ats_score": cv.ats_score,
        "ats_analysis": ats_analysis,
        "created_at": cv.created_at.isoformat()
    }


@router.patch("/{cv_id}")
async def update_cv(
    cv_id: int,
    payload: CVUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update editable extracted CV fields."""
    cv = db.query(CV).filter(
        CV.id == cv_id,
        CV.user_id == current_user.id
    ).first()
    
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )
    
    update_data = payload.model_dump(exclude_unset=True)
    
    for field_name in ["skills", "tech_stack", "job_roles", "keywords"]:
        if field_name in update_data:
            setattr(cv, field_name, clean_string_list(update_data[field_name]))
    
    if "experience_years" in update_data:
        cv.experience_years = update_data["experience_years"]
    
    parsed_data = dict(cv.parsed_data or {})
    parsed_data.update({
        "skills": cv.skills or [],
        "tech_stack": cv.tech_stack or [],
        "job_roles": cv.job_roles or [],
        "keywords": cv.keywords or [],
        "experience_years": cv.experience_years,
    })
    cv.parsed_data = parsed_data
    sync_ats_score(cv)
    cv.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(cv)
    
    return {
        "id": cv.id,
        "file_name": cv.file_name,
        "skills": cv.skills,
        "tech_stack": cv.tech_stack,
        "job_roles": cv.job_roles,
        "keywords": cv.keywords,
        "experience_years": cv.experience_years,
        "ats_score": cv.ats_score,
        "ats_analysis": cv.parsed_data.get("ats_analysis") if cv.parsed_data else None,
        "created_at": cv.created_at.isoformat()
    }


@router.delete("/{cv_id}")
async def delete_cv(
    cv_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a CV."""
    cv = db.query(CV).filter(
        CV.id == cv_id,
        CV.user_id == current_user.id
    ).first()
    
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )
    
    # Delete file from Cloudinary
    try:
        if cv.cloudinary_url:
            delete_file_from_cloudinary(cv.cloudinary_url)
    except Exception:
        pass  # Continue even if Cloudinary deletion fails
    
    db.delete(cv)
    db.commit()
    
    return {"message": "CV deleted successfully"}


@router.post("/{cv_id}/match-jobs")
async def match_jobs_for_cv(
    cv_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Match jobs based on CV and calculate match scores."""
    cv = db.query(CV).filter(
        CV.id == cv_id,
        CV.user_id == current_user.id
    ).first()
    
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )
    
    # First, run scraping to get fresh jobs
    # Use CV's job roles and tech stack as search criteria
    query = " ".join(cv.job_roles or []) if cv.job_roles else "software engineer"
    scrape_request = ScrapeRequest(
        query=query,
        remote_only=True,
        global_or_india=True,
        exclude_indian_hq=True,
        strict_experience=False,
        strict_title=False,
        strict_junior=False,
        send_alerts=False,
        sources=[],  # Empty means all sources
        linkedin_urls=[]
    )
    
    # Run scraping
    scrape_result = run_scrape(
        db=db,
        request=scrape_request,
        user_id=current_user.id
    )
    
    # Get all active jobs after scraping
    jobs = db.query(Job).filter(Job.is_active == True).all()
    db.query(CVJobMatch).filter(CVJobMatch.cv_id == cv.id).delete(synchronize_session=False)
    
    # Calculate match scores for each job
    matches = []
    for job in jobs:
        match_score = calculate_match_score(cv, job)
        
        if match_score > 0:  # Only save if there's some match
            cv_job_match = CVJobMatch(
                cv_id=cv.id,
                job_id=job.id,
                match_score=match_score,
                skills_matched=calculate_matched_skills(cv, job),
                skills_missing=calculate_missing_skills(cv, job),
                experience_match=determine_experience_match(cv, job),
                created_at=datetime.utcnow()
            )
            db.add(cv_job_match)
            matches.append(cv_job_match)
    
    cv.last_scraped_at = datetime.utcnow()
    db.commit()
    
    return {
        "message": f"Scraped {scrape_result.get('jobs_found', 0)} jobs and matched {len(matches)} for CV",
        "matches_count": len(matches),
        "scraped_jobs": scrape_result.get('jobs_found', 0)
    }


@router.get("/{cv_id}/matched-jobs")
async def get_matched_jobs(
    cv_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get jobs matched to a CV, sorted by match score."""
    cv = db.query(CV).filter(
        CV.id == cv_id,
        CV.user_id == current_user.id
    ).first()
    
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )
    
    matches = db.query(CVJobMatch).filter(
        CVJobMatch.cv_id == cv_id
    ).order_by(CVJobMatch.match_score.desc()).limit(50).all()
    
    result = []
    for match in matches:
        job = db.query(Job).filter(Job.id == match.job_id).first()
        if job:
            result.append({
                "match_id": match.id,
                "job_id": job.id,
                "title": job.title,
                "company": job.company,
                "tech_stack": job.tech_stack,
                "location": job.location,
                "url": job.url,
                "match_score": match.match_score,
                "skills_matched": match.skills_matched,
                "skills_missing": match.skills_missing,
                "experience_match": match.experience_match
            })
    
    return result


def calculate_match_score(cv: CV, job: Job) -> int:
    """Calculate match score between CV and job (0-100)."""
    score = 0
    
    # Tech stack matching (35 points)
    cv_tech = set(cv.tech_stack or [])
    job_tech = set((job.tech_stack or "").lower().split(","))
    
    if job_tech:
        matched_tech = cv_tech.intersection(job_tech)
        tech_score = (len(matched_tech) / len(job_tech)) * 35
        score += tech_score
    
    # Job role matching (20 points)
    cv_roles = set(cv.job_roles or [])
    job_title_lower = (job.title or "").lower()
    
    role_matches = 0
    for role in cv_roles:
        if role in job_title_lower:
            role_matches += 1
    
    if cv_roles:
        role_score = (role_matches / len(cv_roles)) * 20
        score += role_score
    
    # Skills matching (20 points)
    cv_skills = set(cv.skills or [])
    job_desc = (job.description or "").lower()
    
    skill_matches = 0
    for skill in cv_skills:
        if skill in job_desc:
            skill_matches += 1
    
    if cv_skills:
        skill_score = (skill_matches / len(cv_skills)) * 20
        score += skill_score
    
    # Keyword matching (15 points)
    cv_keywords = set(cv.keywords or [])
    job_text = (job.title + " " + (job.description or "") + " " + (job.tech_stack or "")).lower()
    
    keyword_matches = 0
    for keyword in cv_keywords:
        if keyword in job_text:
            keyword_matches += 1
    
    if cv_keywords:
        keyword_score = (keyword_matches / len(cv_keywords)) * 15
        score += keyword_score
    
    # Experience matching (10 points)
    if cv.experience_years and job.experience_level:
        if job.experience_level.lower() in ['entry level', 'junior'] and cv.experience_years <= 2:
            score += 10
        elif job.experience_level.lower() in ['mid-senior', 'mid'] and 2 < cv.experience_years <= 5:
            score += 10
        elif job.experience_level.lower() in ['senior', 'lead'] and cv.experience_years > 5:
            score += 10
    
    return min(int(score), 100)


def calculate_matched_skills(cv: CV, job: Job) -> list:
    """Calculate which skills from CV match the job."""
    cv_tech = set(cv.tech_stack or [])
    job_tech = set((job.tech_stack or "").lower().split(","))
    return list(cv_tech.intersection(job_tech))


def calculate_missing_skills(cv: CV, job: Job) -> list:
    """Calculate which skills from job are missing in CV."""
    cv_tech = set(cv.tech_stack or [])
    job_tech = set((job.tech_stack or "").lower().split(","))
    return list(job_tech - cv_tech)


def determine_experience_match(cv: CV, job: Job) -> str:
    """Determine if experience level matches."""
    if not cv.experience_years or not job.experience_level:
        return "unknown"
    
    job_level = job.experience_level.lower()
    if job_level in ['entry level', 'junior'] and cv.experience_years <= 2:
        return "high"
    elif job_level in ['mid-senior', 'mid'] and 2 < cv.experience_years <= 5:
        return "high"
    elif job_level in ['senior', 'lead'] and cv.experience_years > 5:
        return "high"
    elif job_level in ['entry level', 'junior'] and cv.experience_years <= 3:
        return "medium"
    else:
        return "low"
