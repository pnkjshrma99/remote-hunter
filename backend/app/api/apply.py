"""API endpoint for one-click job application + autofill assistant."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models.cv import CV
from app.models.job import Job
from app.models.user import User
from app.models.user_job import UserJobApplication
from app.services.apply_automation import apply_to_job
from app.services.user_profile import UserProfileService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["apply"])


class ApplyResponse(BaseModel):
    success: bool
    message: str
    ats_type: str = ""


class AutofillField(BaseModel):
    label: str
    value: str
    field_type: str = "text"


class AutofillSection(BaseModel):
    title: str
    fields: List[AutofillField]


class AutofillResponse(BaseModel):
    job_url: str
    job_title: str
    company: str
    sections: List[AutofillSection]
    resume_url: str = ""
    resume_name: str = ""


@router.post("/{job_id}/apply", response_model=ApplyResponse)
def apply_for_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    profile_service: UserProfileService = Depends(),
    db: Session = Depends(get_db),
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    profile = profile_service.get_or_create(current_user.id)

    existing_application = db.query(UserJobApplication).filter(
        UserJobApplication.user_id == current_user.id,
        UserJobApplication.job_id == job_id,
    ).first()

    if existing_application:
        return ApplyResponse(
            success=True,
            message="Already applied to this job.",
            ats_type="cached",
        )

    result = apply_to_job(
        job=job,
        profile=profile,
        user_email=current_user.email or "",
        user_name=current_user.full_name or "",
    )

    if result.success:
        db.add(UserJobApplication(user_id=current_user.id, job_id=job.id))
        db.commit()
        logger.info(
            "User %d applied to job %d (%s) via %s",
            current_user.id,
            job.id,
            job.title,
            result.ats_type,
        )

    return ApplyResponse(
        success=result.success,
        message=result.message,
        ats_type=result.ats_type,
    )


@router.post("/{job_id}/autofill", response_model=AutofillResponse)
def autofill_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    profile_service: UserProfileService = Depends(),
    db: Session = Depends(get_db),
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    profile = profile_service.get_or_create(current_user.id)

    sections: List[AutofillSection] = []

    # Personal Information
    personal = AutofillSection(title="Personal Information", fields=[])
    if current_user.full_name:
        personal.fields.append(AutofillField(label="Full Name", value=current_user.full_name))
    if current_user.email:
        personal.fields.append(AutofillField(label="Email", value=current_user.email))
    if profile.phone:
        personal.fields.append(AutofillField(label="Phone", value=profile.phone))
    if profile.address:
        personal.fields.append(AutofillField(label="Address", value=profile.address))
    if profile.city:
        personal.fields.append(AutofillField(label="City", value=profile.city))
    if profile.country:
        personal.fields.append(AutofillField(label="Country", value=profile.country))
    if personal.fields:
        sections.append(personal)

    # Social & Links
    social = AutofillSection(title="Social & Links", fields=[])
    if profile.linkedin_url:
        social.fields.append(AutofillField(label="LinkedIn URL", value=profile.linkedin_url))
    if profile.github_url:
        social.fields.append(AutofillField(label="GitHub URL", value=profile.github_url))
    if profile.portfolio_url:
        social.fields.append(AutofillField(label="Portfolio URL", value=profile.portfolio_url))
    if profile.website:
        social.fields.append(AutofillField(label="Website", value=profile.website))
    if social.fields:
        sections.append(social)

    # Professional Summary
    if profile.headline:
        sections.append(AutofillSection(title="Professional Headline", fields=[
            AutofillField(label="Headline", value=profile.headline),
        ]))
    if profile.summary:
        sections.append(AutofillSection(title="Summary", fields=[
            AutofillField(label="Professional Summary", value=profile.summary, field_type="textarea"),
        ]))

    # Work Experience
    for exp in (profile.experiences or []):
        exp_fields = [
            AutofillField(label="Company", value=exp.company),
            AutofillField(label="Title", value=exp.title),
            AutofillField(label="Start Date", value=exp.start_date),
        ]
        if exp.end_date:
            exp_fields.append(AutofillField(label="End Date", value=exp.end_date))
        if exp.location:
            exp_fields.append(AutofillField(label="Location", value=exp.location))
        if exp.description:
            exp_fields.append(AutofillField(label="Description", value=exp.description, field_type="textarea"))
        if exp.tech_used:
            exp_fields.append(AutofillField(label="Technologies Used", value=", ".join(exp.tech_used)))
        sections.append(AutofillSection(title=f"Experience: {exp.title} @ {exp.company}", fields=exp_fields))

    # Education
    for edu in (profile.education or []):
        edu_fields = [
            AutofillField(label="School", value=edu.school),
            AutofillField(label="Degree", value=edu.degree),
        ]
        if edu.field_of_study:
            edu_fields.append(AutofillField(label="Field of Study", value=edu.field_of_study))
        if edu.start_date:
            edu_fields.append(AutofillField(label="Start Date", value=edu.start_date))
        if edu.end_date:
            edu_fields.append(AutofillField(label="End Date", value=edu.end_date))
        if edu.gpa:
            edu_fields.append(AutofillField(label="GPA", value=edu.gpa))
        sections.append(AutofillSection(title=f"Education: {edu.degree} @ {edu.school}", fields=edu_fields))

    # Preferences
    prefs = AutofillSection(title="Job Preferences", fields=[])
    if profile.desired_roles:
        prefs.fields.append(AutofillField(label="Desired Roles", value=", ".join(profile.desired_roles)))
    if profile.preferred_locations:
        prefs.fields.append(AutofillField(label="Preferred Locations", value=", ".join(profile.preferred_locations)))
    if profile.desired_salary_min or profile.desired_salary_max:
        salary = f"{profile.desired_salary_currency or 'USD'} {profile.desired_salary_min or '—'} – {profile.desired_salary_max or '—'}"
        prefs.fields.append(AutofillField(label="Desired Salary", value=salary))
    prefs.fields.append(AutofillField(label="Remote Only", value="Yes" if profile.remote_only else "No"))
    prefs.fields.append(AutofillField(label="Open to Relocation", value="Yes" if profile.open_to_relocation else "No"))
    if prefs.fields:
        sections.append(prefs)

    # Cover Letter
    if profile.cover_letter_intro:
        sections.append(AutofillSection(title="Cover Letter", fields=[
            AutofillField(label="Cover Letter", value=profile.cover_letter_intro, field_type="textarea"),
        ]))

    existing = db.query(UserJobApplication).filter(
        UserJobApplication.user_id == current_user.id,
        UserJobApplication.job_id == job.id,
    ).first()
    if not existing:
        db.add(UserJobApplication(user_id=current_user.id, job_id=job.id))
        db.commit()

    latest_cv = (
        db.query(CV)
        .filter(CV.user_id == current_user.id)
        .order_by(CV.created_at.desc())
        .first()
    )

    return AutofillResponse(
        job_url=job.url or "",
        job_title=job.title,
        company=job.company,
        sections=sections,
        resume_url=latest_cv.cloudinary_url if latest_cv else "",
        resume_name=latest_cv.file_name if latest_cv else "",
    )
