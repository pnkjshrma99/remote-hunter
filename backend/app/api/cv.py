"""CV upload and management API endpoints."""

import os
import shutil
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
import PyPDF2
from docx import Document

from app.database import get_db
from app.models.cv import CV, CVJobMatch
from app.models.user import User
from app.models.job import Job
from app.services.cv_parser import CVParser
from app.services.jobs import run_scrape
from app.schemas.job import ScrapeRequest
from app.api.auth import get_current_user

router = APIRouter(prefix="/cv", tags=["cv"])

# Upload directory for CVs
UPLOAD_DIR = "uploads/cvs"
os.makedirs(UPLOAD_DIR, exist_ok=True)


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
    
    # Generate unique filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{current_user.id}_{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Extract text from file
    try:
        if file_ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        elif file_ext == '.pdf':
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        elif file_ext in ['.docx', '.doc']:
            doc = Document(file_path)
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
        file_path=file_path,
        file_name=file.filename,
        file_size=os.path.getsize(file_path),
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
    
    db.add(cv)
    db.commit()
    db.refresh(cv)
    
    return {
        "id": cv.id,
        "file_name": cv.file_name,
        "skills": cv.skills,
        "tech_stack": cv.tech_stack,
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
    
    return [
        {
            "id": cv.id,
            "file_name": cv.file_name,
            "skills": cv.skills,
            "tech_stack": cv.tech_stack,
            "experience_years": cv.experience_years,
            "created_at": cv.created_at.isoformat(),
            "ats_score": cv.ats_score
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
    
    return {
        "id": cv.id,
        "file_name": cv.file_name,
        "skills": cv.skills,
        "tech_stack": cv.tech_stack,
        "experience_years": cv.experience_years,
        "education": cv.education,
        "certifications": cv.certifications,
        "parsed_data": cv.parsed_data,
        "ats_score": cv.ats_score,
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
    
    # Delete file from disk
    try:
        if os.path.exists(cv.file_path):
            os.remove(cv.file_path)
    except Exception:
        pass  # Continue even if file deletion fails
    
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
