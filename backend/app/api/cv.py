"""CV upload and management API endpoints."""

import os
import re
import shutil
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, BackgroundTasks, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session
import PyPDF2
from docx import Document

from app.database import get_db

logger = logging.getLogger(__name__)
from app.models.cv import CV, CVJobMatch
from app.models.user import User
from app.models.job import Job
from app.services.cv_parser import CVParser
from app.services.jobs import run_scrape, get_scrape_freshness
from app.config import get_settings
from app.services.cloudinary_service import upload_bytes_to_cloudinary, delete_file_from_cloudinary
from app.schemas.job import ScrapeRequest
from app.api.auth import get_current_user
from scrapers.filters import expand_query

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
    
    # 1. ATS-readable sections (max 15)
    sections_score = min(15,
        (tech_count > 0) * 3 + (role_count > 0) * 3 +
        (cv.experience_years is not None) * 3 + (education_count > 0) * 3 +
        (keyword_count > 0) * 3
    )
    
    # 2. Skills and tech depth (max 20)
    skills_score = min(20, tech_count * 1.5 + skill_count * 0.5)
    
    # 3. Experience clarity (max 15)
    experience_score = 0
    if cv.experience_years is not None:
        experience_score = 5 if cv.experience_years <= 2 else 10 if cv.experience_years <= 5 else 15
    
    # 4. Target role alignment (max 15)
    role_score = min(15, role_count * 5)
    
    # 5. Keyword coverage & density (max 15)
    keyword_score = min(15, keyword_count * 1.5)
    
    # 6. Education and certifications (max 10)
    credential_score = min(10, education_count * 3 + certification_count * 2)
    
    # 7. Format & parsability (max 10) — checks if parsed data has sufficient text
    parsed = cv.parsed_data or {}
    raw_text_length = len(str(parsed.get("keywords", []))) + skill_count * 2
    format_score = 5 if raw_text_length > 20 else 0
    
    score = sections_score + skills_score + experience_score + role_score + keyword_score + credential_score + format_score
    score = max(0, min(int(score), 100))
    
    recommendations = []
    if tech_count < 6:
        recommendations.append("Add more concrete tools, frameworks, and languages from your recent work.")
    if role_count == 0:
        recommendations.append("Add a clear target role such as backend developer, data engineer, or DevOps engineer.")
    if cv.experience_years is None:
        recommendations.append("Add total years of professional experience in a simple ATS-readable format.")
    if keyword_count < 8:
        recommendations.append("Add measurable project keywords from job descriptions you are targeting.")
    if education_count == 0 and certification_count == 0:
        recommendations.append("Add education or relevant certifications if they apply.")
    if format_score < 10:
        recommendations.append("Use standard section headers (Experience, Education, Skills) for better ATS parsing.")
    if not recommendations:
        recommendations.append("Your CV has strong ATS coverage. Tune keywords for each job description before applying.")
    
    return {
        "score": score,
        "rating": "Strong" if score >= 80 else "Good" if score >= 60 else "Needs work",
        "breakdown": [
            {"label": "ATS-readable sections", "score": int(sections_score), "max_score": 15},
            {"label": "Skills and tech depth", "score": int(skills_score), "max_score": 20},
            {"label": "Experience clarity", "score": experience_score, "max_score": 15},
            {"label": "Target role alignment", "score": role_score, "max_score": 15},
            {"label": "Keyword coverage", "score": int(keyword_score), "max_score": 15},
            {"label": "Education and certifications", "score": credential_score, "max_score": 10},
            {"label": "Format & parsability", "score": format_score, "max_score": 10},
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
    # Preserve status field (pending/completed/failed)
    status = parsed_data.get("status")
    parsed_data["ats_analysis"] = analysis
    if status:
        parsed_data["status"] = status
    cv.parsed_data = parsed_data
    return analysis


@router.post("/upload")
async def upload_cv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Upload a CV file. Parsing happens in background — poll GET /cv/{id} for results."""
    
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
    
    # Upload to Cloudinary (optional — saves locally if not configured)
    cloudinary_url = ""
    try:
        result = upload_bytes_to_cloudinary(
            file_bytes=file_content,
            filename=file.filename,
            folder=f"cvs/user_{current_user.id}",
            resource_type="raw"
        )
        if result and result[0]:
            cloudinary_url, upload_result = result
    except Exception:
        pass
    
    if not cloudinary_url:
        # Fall back to local storage
        local_dir = os.path.join(UPLOAD_DIR, f"user_{current_user.id}")
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, file.filename)
        with open(local_path, "wb") as f:
            f.write(file_content)
        cloudinary_url = local_path
    
    # Create CV record immediately with parsing_status="pending"
    cv = CV(
        user_id=current_user.id,
        cloudinary_url=cloudinary_url,
        file_name=file.filename,
        file_size=file_size,
        content_type=file.content_type,
        parsed_data={"status": "pending"},
        skills=[],
        tech_stack=[],
        job_roles=[],
        keywords=[],
        experience_years=None,
        education=[],
        certifications=[],
        created_at=datetime.utcnow()
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)

    # Parse in background
    background_tasks.add_task(_parse_cv_background, cv.id, file_content, file_ext, db)

    return {
        "id": cv.id,
        "file_name": cv.file_name,
        "status": "pending",
        "message": "CV uploaded. Parsing in progress..."
    }


def _parse_cv_background(cv_id: int, file_content: bytes, file_ext: str, db: Session) -> None:
    """Parse CV content in background and update the DB record."""
    try:
        # Extract text
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

        parsed_data = CVParser.parse_cv(text)

        # Re-fetch CV and update
        cv = db.query(CV).filter(CV.id == cv_id).first()
        if not cv:
            return

        cv.parsed_data = parsed_data
        cv.skills = parsed_data['skills']
        cv.tech_stack = parsed_data['tech_stack']
        cv.job_roles = parsed_data.get('job_roles', [])
        cv.keywords = parsed_data.get('keywords', [])
        cv.experience_years = parsed_data['experience_years']
        cv.education = parsed_data['education']
        cv.certifications = parsed_data['certifications']
        sync_ats_score(cv)
        cv.parsed_data["status"] = "completed"
        cv.updated_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.error(f"Background CV parsing failed for cv_id={cv_id}: {e}", exc_info=True)
        try:
            cv = db.query(CV).filter(CV.id == cv_id).first()
            if cv:
                cv.parsed_data = {"status": "failed", "error": str(e)}
                db.commit()
        except Exception:
            pass


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
    
    # Delete file from Cloudinary or local storage
    try:
        if cv.cloudinary_url:
            if cv.cloudinary_url.startswith("http"):
                deleted = delete_file_from_cloudinary(cv.cloudinary_url)
                if not deleted:
                    print(f"Warning: failed to delete Cloudinary file: {cv.cloudinary_url}")
            else:
                # Local file
                if os.path.exists(cv.cloudinary_url):
                    os.remove(cv.cloudinary_url)
    except Exception:
        pass  # Continue even if deletion fails
    
    db.delete(cv)
    db.commit()
    
    return {"message": "CV deleted successfully"}


@router.post("/{cv_id}/match-jobs")
async def match_jobs_for_cv(
    cv_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Match jobs based on CV and calculate match scores.
    
    Uses cached jobs if they're fresh enough — only re-scrapes if stale.
    """
    cv = db.query(CV).filter(
        CV.id == cv_id,
        CV.user_id == current_user.id
    ).first()
    
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )
    
    settings = get_settings()
    freshness = get_scrape_freshness(db)
    needs_scrape = not freshness["is_fresh"] or freshness["active_jobs_count"] == 0

    if needs_scrape:
        # Use CV's job roles and tech stack as search criteria
        query = " ".join(cv.job_roles or []) if cv.job_roles else "software engineer"
        # Expand query to include related role titles (e.g. "DevOps Engineer" → also "SRE", "Platform Engineer")
        expanded_query = expand_query(query)
        if expanded_query != query:
            logger.info(f"Expanded query: '{query}' → '{expanded_query}'")
        scrape_request = ScrapeRequest(
            query=expanded_query,
            remote_only=True,
            global_or_india=True,
            exclude_indian_hq=True,
            strict_experience=False,
            strict_title=False,
            strict_junior=False,
            send_alerts=False,
            sources=[],
            linkedin_urls=[]
        )
        scrape_result = run_scrape(
            db=db,
            request=scrape_request,
            user_id=current_user.id
        )
        scraped_jobs = scrape_result.get('jobs_found', 0)
        scrape_info = f"Scraped {scraped_jobs} jobs"
    else:
        scraped_jobs = freshness["active_jobs_count"]
        scrape_info = f"Using {scraped_jobs} cached jobs (last scraped {freshness['stale_in_hours']}h ago)"
    
    # Get all active jobs
    jobs = db.query(Job).filter(Job.is_active == True).all()
    db.query(CVJobMatch).filter(CVJobMatch.cv_id == cv.id).delete(synchronize_session=False)
    
    # Calculate match scores for each job (parallel)
    from concurrent.futures import ThreadPoolExecutor, as_completed
    matches: list[CVJobMatch] = []
    match_lock = __import__("threading").Lock()

    def _score_job(job: Job) -> CVJobMatch | None:
        score = calculate_match_score(cv, job)
        if score > 0:
            return CVJobMatch(
                cv_id=cv.id,
                job_id=job.id,
                match_score=score,
                skills_matched=calculate_matched_skills(cv, job),
                skills_missing=calculate_missing_skills(cv, job),
                experience_match=determine_experience_match(cv, job),
                created_at=datetime.utcnow()
            )
        return None

    with ThreadPoolExecutor(max_workers=min(len(jobs), 20)) as executor:
        futures = {executor.submit(_score_job, job): job for job in jobs}
        for future in as_completed(futures):
            result = future.result()
            if result:
                with match_lock:
                    db.add(result)
                    matches.append(result)
    
    cv.last_scraped_at = datetime.utcnow()
    db.commit()
    
    return {
        "message": f"{scrape_info} and matched {len(matches)} for CV",
        "matches_count": len(matches),
        "scraped_jobs": scraped_jobs
    }


@router.get("/{cv_id}/matched-jobs")
async def get_matched_jobs(
    cv_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    posted_within_days: Optional[int] = Query(None, description="Filter jobs posted within N days")
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
    
    query = db.query(CVJobMatch).filter(
        CVJobMatch.cv_id == cv_id
    )
    
    if posted_within_days:
        cutoff = datetime.utcnow() - timedelta(days=posted_within_days)
        query = query.join(Job, CVJobMatch.job_id == Job.id).filter(Job.posted_at >= cutoff)
    
    matches = query.order_by(CVJobMatch.match_score.desc()).limit(50).all()
    
    result = []
    for match in matches:
        job = db.query(Job).filter(Job.id == match.job_id).first()
        if job:
            analysis = build_match_analysis(job, match)
            result.append({
                "match_id": match.id,
                "job_id": job.id,
                "title": job.title,
                "company": job.company,
                "tech_stack": job.tech_stack,
                "description": (job.description or "")[:500],
                "location": job.location,
                "url": job.url,
                "match_score": match.match_score,
                "skills_matched": match.skills_matched or [],
                "skills_missing": match.skills_missing or [],
                "experience_match": match.experience_match or "unknown",
                "is_applied": job.is_applied if hasattr(job, 'is_applied') else False,
                "analysis": analysis,
            })
    
    return result


def calculate_match_score(cv: CV, job: Job) -> int:
    """Calculate match score between CV and job (0-100) using multi-dimensional analysis.
    
    Categories:
    - Tech stack alignment: 0-25
    - Role/title similarity: 0-20
    - Description keyword density: 0-20
    - Experience relevance: 0-15
    - Seniority level match: 0-10
    - Remote/location fit: 0-5
    - Job quality bonus: 0-5
    """
    score = 0

    # --- 1. Tech stack alignment (25 points) ---
    cv_tech = set(t.strip().lower() for t in (cv.tech_stack or []) if t.strip())
    job_raw = (job.tech_stack or "").lower()
    job_tech = set(t.strip() for t in job_raw.split(",") if t.strip()) if job_raw else set()
    job_desc_lower = (job.description or "").lower()
    job_full_text = f"{job.title or ''} {job_desc_lower} {job_raw}".lower()

    tech_score = 0
    if cv_tech:
        # Direct tech_stack field match (15 pts)
        if job_tech:
            matched_tech = cv_tech.intersection(job_tech)
            tech_score += (len(matched_tech) / max(len(job_tech), 1)) * 15
            remaining = cv_tech - job_tech
        else:
            remaining = cv_tech

        # Description word-match for remaining tech (10 pts)
        if remaining:
            desc_matches = sum(1 for t in remaining if t in job_full_text)
            tech_score += (desc_matches / len(cv_tech)) * 10

    score += min(tech_score, 25)

    # --- 2. Role/title similarity (20 points) ---
    cv_roles = [r.lower().strip() for r in (cv.job_roles or []) if r.strip()]
    job_title_lower = (job.title or "").lower()

    role_score = 0
    if cv_roles and job_title_lower:
        title_words = set(re.findall(r"[a-zA-Z0-9+#.]+", job_title_lower))
        for role in cv_roles:
            role_words = set(re.findall(r"[a-zA-Z0-9+#.]+", role))
            if not role_words:
                continue
            common = role_words.intersection(title_words)
            if common:
                word_coverage = len(common) / max(len(role_words), 1)
                if role in job_title_lower:
                    word_coverage = 1.0
                # Weight by word rarity (common words like "engineer" get less weight)
                rare_ratio = sum(
                    1 for w in common
                    if w not in {"engineer", "developer", "software", "remote", "senior", "junior", "lead"}
                ) / max(len(common), 1)
                weighted = word_coverage * (0.3 + 0.7 * rare_ratio)
                role_score += weighted * (20 / max(len(cv_roles), 1))

    score += min(role_score, 20)

    # --- 3. Description keyword density (20 points) ---
    cv_keywords = set(k.lower().strip() for k in (cv.keywords or []) if k.strip())
    cv_skills = set(s.lower().strip() for s in (cv.skills or []) if s.strip())
    all_terms = cv_keywords | cv_skills

    desc_score = 0
    if all_terms and job_desc_lower:
        desc_matches = sum(1 for t in all_terms if t in job_full_text)
        desc_score = (desc_matches / max(len(all_terms), 1)) * 20
        # Bonus for dense matching (>60% terms matched)
        if desc_matches / max(len(all_terms), 1) > 0.6:
            desc_score = min(desc_score * 1.2, 20)
    elif all_terms and not job_desc_lower:
        desc_score = 5  # No description available, partial credit

    score += min(desc_score, 20)

    # --- 4. Experience relevance (15 points) ---
    exp_score = 0
    if cv.experience_years is not None:
        cy = cv.experience_years
        if job.experience_level:
            exp_level = job.experience_level.lower()
            # Parse experience from description as well
            desc_exp = _extract_experience_years(job_desc_lower)

            if exp_level in ("entry level", "junior", "intern") and cy <= 3:
                exp_score = 15
            elif exp_level in ("mid-senior", "mid", "mid_level") and 2 <= cy <= 6:
                exp_score = 15
            elif exp_level in ("senior", "staff", "lead") and cy >= 4:
                exp_score = 15
            elif exp_level in ("director", "principal", "manager") and cy >= 6:
                exp_score = 15
            elif exp_level in ("vp", "executive") and cy >= 8:
                exp_score = 15
            elif desc_exp:
                desc_min, desc_max = desc_exp
                if desc_min is not None and cy >= desc_min - 1:
                    exp_score = min(15, 5 + (cy / max(desc_max or cy + 2, 1)) * 10)
                else:
                    exp_score = 5
            else:
                exp_score = 8  # Partial for any experience with unknown level
        elif desc_exp := _extract_experience_years(job_desc_lower):
            desc_min, desc_max = desc_exp
            if desc_min is not None and cy >= desc_min - 1:
                exp_score = min(15, 5 + (cy / max(desc_max or cy + 2, 1)) * 10)
            else:
                exp_score = 5
        else:
            exp_score = 10  # No experience info in job, give moderate credit
    else:
        exp_score = 5  # No CV experience info

    score += min(exp_score, 15)

    # --- 5. Seniority level match (10 points) ---
    seniority_score = 0
    if job.seniority_tag:
        job_senior = job.seniority_tag.lower()
        job_seniority_order = {
            "intern": 0, "entry level": 0, "junior": 1,
            "mid": 2, "mid-senior": 2, "mid_level": 2,
            "senior": 3, "staff": 3, "lead": 3,
            "principal": 4, "manager": 4, "director": 5,
            "vp": 6, "executive": 6,
        }
        cv_seniority_map = {
            "entry level": 0, "junior": 1, "mid": 2,
            "senior": 3, "lead": 3, "manager": 4,
            "director": 5, "executive": 6,
        }

        if cv.experience_years is not None:
            cy = cv.experience_years
            if cy <= 2:
                cv_senior = "junior"
            elif cy <= 5:
                cv_senior = "mid"
            elif cy <= 8:
                cv_senior = "senior"
            else:
                cv_senior = "lead"

            job_level = job_seniority_order.get(job_senior, 2)
            cv_level = cv_seniority_map.get(cv_senior, 2)
            diff = abs(job_level - cv_level)
            if diff == 0:
                seniority_score = 10
            elif diff == 1:
                seniority_score = 7
            elif diff == 2:
                seniority_score = 4
            else:
                seniority_score = 2

    score += seniority_score

    # --- 6. Remote/location fit (5 points) ---
    location_score = 0
    if job.is_verified_remote:
        location_score = 5
    elif job.region_eligibility:
        region = job.region_eligibility.lower()
        if "remote" in region or "worldwide" in region or "global" in region:
            location_score = 5
        elif "anywhere" in region:
            location_score = 5
        else:
            location_score = 2
    else:
        # Check description for remote indicators
        if job_desc_lower:
            remote_words = {"remote", "worldwide", "anywhere", "global", "fully remote"}
            if remote_words.intersection(job_desc_lower.split()):
                location_score = 4

    score += location_score

    # --- 7. Job quality bonus (5 points) ---
    quality_score = 0
    if job.description and len(job.description) >= 300:
        quality_score += 2  # Detailed description
    if job.salary_min and job.salary_max and job.salary_max > job.salary_min:
        quality_score += 2  # Has salary range
    if job.skills and len(job.skills) >= 3:
        quality_score += 1  # Structured skills
    if job.tech_stack and len(job.tech_stack) > 0:
        quality_score += 1  # Tech stack listed

    score += min(quality_score, 5)

    return min(int(score), 100)


def _extract_experience_years(text: str):
    """Extract experience year range from text like '3-5 years' or '5+ years'."""
    if not text:
        return None
    range_match = re.search(r"(\d{1,2})\s*[-–to]+\s*(\d{1,2})\s*(?:years?|yrs?)", text, re.I)
    if range_match:
        return (int(range_match.group(1)), int(range_match.group(2)))
    plus_match = re.search(r"(\d{1,2})\s*\+\s*(?:years?|yrs?)", text, re.I)
    if plus_match:
        return (int(plus_match.group(1)), None)
    single_match = re.search(r"(\d{1,2})\s*(?:years?|yrs?)", text, re.I)
    if single_match:
        val = int(single_match.group(1))
        if val <= 20:
            return (val, val)
    return None


def calculate_matched_skills(cv: CV, job: Job) -> list:
    """Calculate which CV skills/tech match the job description."""
    cv_tech = set(t.strip().lower() for t in (cv.tech_stack or []) if t.strip())
    job_tech = set(t.strip() for t in ((job.tech_stack or "").lower().split(",")) if t.strip())
    job_desc = (job.description or "").lower()
    job_title = (job.title or "").lower()

    matched = set()
    for tech in cv_tech:
        if tech in job_tech or tech in job_desc or tech in job_title:
            matched.add(tech)

    return sorted(matched)


def calculate_missing_skills(cv: CV, job: Job) -> list:
    """Calculate which job-required skills are missing from CV."""
    cv_tech = set(t.strip().lower() for t in (cv.tech_stack or []) if t.strip())
    cv_skills = set(s.lower().strip() for s in (cv.skills or []) if s.strip())
    cv_all = cv_tech | cv_skills

    job_tech = set(t.strip() for t in ((job.tech_stack or "").lower().split(",")) if t.strip())
    job_desc = (job.description or "").lower()

    # Find tech mentioned in job but not in CV
    job_mentioned = set()
    for tech in job_tech:
        if tech not in cv_all:
            job_mentioned.add(tech)

    # Also check description for common tech keywords
    common_tech = {"python", "javascript", "typescript", "react", "node", "aws",
                   "docker", "kubernetes", "sql", "git", "java", "go", "rust"}
    for tech in common_tech:
        if tech in job_desc and tech not in cv_all:
            job_mentioned.add(tech)

    return sorted(job_mentioned)


def determine_experience_match(cv: CV, job: Job) -> str:
    """Determine how well CV experience matches job requirements."""
    if not cv.experience_years:
        return "unknown"

    cy = cv.experience_years
    job_desc = (job.description or "").lower()
    desc_exp = _extract_experience_years(job_desc)

    if job.experience_level:
        level = job.experience_level.lower()
        if level in ("entry level", "junior") and cy <= 3:
            return "high"
        elif level in ("mid-senior", "mid") and 2 <= cy <= 6:
            return "high"
        elif level in ("senior", "lead") and cy >= 4:
            return "high"
        elif level in ("director", "executive") and cy >= 8:
            return "high"

    if desc_exp:
        desc_min, desc_max = desc_exp
        if desc_min and cy >= desc_min - 1:
            return "high" if cy <= (desc_max or 99) else "medium"
        return "medium" if desc_min and cy >= desc_min - 2 else "low"

    if cy <= 2:
        return "entry"
    elif cy <= 5:
        return "mid"
    else:
        return "senior"


def build_match_analysis(job: Job, match: "CVJobMatch") -> dict:
    """Build a structured analysis of why/how the CV matches a job."""
    matched = match.skills_matched or []
    missing = match.skills_missing or []
    score = match.match_score or 0

    strengths = []
    if matched:
        strengths.append(f"Your CV matches {len(matched)} skill(s): {', '.join(matched[:5])}")
    if match.experience_match == "high":
        strengths.append("Your experience level is well-aligned with this role")
    if job.is_verified_remote:
        strengths.append("This position supports fully remote work")

    gaps = []
    if missing:
        gaps.append(f"You're missing {len(missing)} skill(s) requested: {', '.join(missing[:5])}")
    if match.experience_match == "low":
        gaps.append("Your experience level may differ from what's required")

    suggestions = []
    if missing:
        suggestions.append(f"Highlight transferable skills that overlap with: {', '.join(missing[:3])}")
    if score < 60 and matched:
        suggestions.append("Tailor your CV to emphasize the matched skills more prominently")
    if job.description and len(job.description) > 100:
        suggestions.append("Review the job description for specific keywords to incorporate")
    if not suggestions:
        suggestions.append("Your profile is a strong match — no major gaps detected")

    return {
        "score_interpretation": (
            "Strong match" if score >= 80 else
            "Good match" if score >= 60 else
            "Moderate match" if score >= 40 else
            "Low match"
        ),
        "strengths": strengths,
        "gaps": gaps,
        "suggestions": suggestions,
    }
