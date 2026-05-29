"""API endpoints for extended user profile."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.cv import CV
from app.models.user import User
from app.schemas.user_profile import (
    EducationCreate,
    EducationSchema,
    UserProfileCreate,
    UserProfileResponse,
    UserProfileUpdate,
    WorkExperienceCreate,
    WorkExperienceSchema,
)
from app.services.user_profile import UserProfileService

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=UserProfileResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
    service: UserProfileService = Depends(),
):
    profile = service.get(current_user.id)
    if not profile:
        return UserProfileResponse(
            user_id=current_user.id, id=0,
            full_name=current_user.full_name,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            middle_name=current_user.middle_name,
        )
    # Populate name fields from User record
    profile.full_name = current_user.full_name
    profile.first_name = current_user.first_name
    profile.last_name = current_user.last_name
    profile.middle_name = current_user.middle_name
    return profile


@router.put("", response_model=UserProfileResponse)
def update_profile(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    service: UserProfileService = Depends(),
    db: Session = Depends(get_db),
):
    profile = service.update(current_user.id, data)
    # Also update name fields on the User record
    if data.first_name is not None or data.last_name is not None or data.middle_name is not None:
        if data.first_name is not None:
            current_user.first_name = data.first_name
        if data.last_name is not None:
            current_user.last_name = data.last_name
        if data.middle_name is not None:
            current_user.middle_name = data.middle_name
        parts = [current_user.first_name or ""]
        if current_user.middle_name:
            parts.append(current_user.middle_name)
        parts.append(current_user.last_name or "")
        current_user.full_name = " ".join(p.strip() for p in parts if p.strip()) or None
        db.commit()
    # Populate name fields from User record for response
    profile.full_name = current_user.full_name
    profile.first_name = current_user.first_name
    profile.last_name = current_user.last_name
    profile.middle_name = current_user.middle_name
    return profile


@router.post("", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(
    data: UserProfileCreate,
    current_user: User = Depends(get_current_user),
    service: UserProfileService = Depends(),
):
    existing = service.get(current_user.id)
    if existing and existing.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile already exists. Use PUT to update.",
        )
    profile = service.get_or_create(current_user.id)
    update_data = data.model_dump(exclude={"experiences", "education"}, exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)
    for exp_data in (data.experiences or []):
        service.add_experience(current_user.id, exp_data)
    for edu_data in (data.education or []):
        service.add_education(current_user.id, edu_data)
    service.db.commit()
    service.db.refresh(profile)
    return profile


@router.post("/experiences", response_model=WorkExperienceSchema, status_code=status.HTTP_201_CREATED)
def add_experience(
    data: WorkExperienceCreate,
    current_user: User = Depends(get_current_user),
    service: UserProfileService = Depends(),
):
    return service.add_experience(current_user.id, data)


@router.put("/experiences/{experience_id}", response_model=WorkExperienceSchema)
def update_experience(
    experience_id: int,
    data: WorkExperienceCreate,
    current_user: User = Depends(get_current_user),
    service: UserProfileService = Depends(),
):
    result = service.update_experience(experience_id, current_user.id, data)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")
    return result


@router.delete("/experiences/{experience_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_experience(
    experience_id: int,
    current_user: User = Depends(get_current_user),
    service: UserProfileService = Depends(),
):
    if not service.delete_experience(experience_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")


@router.post("/education", response_model=EducationSchema, status_code=status.HTTP_201_CREATED)
def add_education(
    data: EducationCreate,
    current_user: User = Depends(get_current_user),
    service: UserProfileService = Depends(),
):
    return service.add_education(current_user.id, data)


@router.put("/education/{education_id}", response_model=EducationSchema)
def update_education(
    education_id: int,
    data: EducationCreate,
    current_user: User = Depends(get_current_user),
    service: UserProfileService = Depends(),
):
    result = service.update_education(education_id, current_user.id, data)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Education not found")
    return result


@router.delete("/education/{education_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_education(
    education_id: int,
    current_user: User = Depends(get_current_user),
    service: UserProfileService = Depends(),
):
    if not service.delete_education(education_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Education not found")


class AutofillField(BaseModel):
    label: str
    value: str
    field_type: str = "text"


class AutofillSection(BaseModel):
    title: str
    fields: List[AutofillField]


class AutofillProfileData(BaseModel):
    sections: List[AutofillSection]
    resume_url: str = ""
    resume_name: str = ""


@router.get("/autofill-data", response_model=AutofillProfileData)
def get_autofill_data(
    current_user: User = Depends(get_current_user),
    service: UserProfileService = Depends(),
    db: Session = Depends(get_db),
):
    profile = service.get_or_create(current_user.id)
    sections: List[AutofillSection] = []

    personal = AutofillSection(title="Personal Information", fields=[])
    if current_user.first_name:
        personal.fields.append(AutofillField(label="First Name", value=current_user.first_name))
    if current_user.last_name:
        personal.fields.append(AutofillField(label="Last Name", value=current_user.last_name))
    if current_user.first_name or current_user.last_name:
        personal.fields.append(AutofillField(
            label="Full Name",
            value=f"{current_user.first_name or ''} {current_user.last_name or ''}".strip()
        ))
    if current_user.middle_name:
        personal.fields.append(AutofillField(label="Middle Name", value=current_user.middle_name))
    if current_user.email:
        personal.fields.append(AutofillField(label="Email", value=current_user.email))
    if profile.phone:
        personal.fields.append(AutofillField(label="Phone", value=profile.phone))
    if profile.city or profile.country:
        loc_parts = [p for p in [profile.city, profile.state, profile.country] if p]
        personal.fields.append(AutofillField(label="Location", value=", ".join(loc_parts)))
    if profile.postal_code:
        personal.fields.append(AutofillField(label="Postal Code", value=profile.postal_code))
    if profile.state:
        personal.fields.append(AutofillField(label="State", value=profile.state))
    if profile.address:
        personal.fields.append(AutofillField(label="Address", value=profile.address))
    if profile.city:
        personal.fields.append(AutofillField(label="City", value=profile.city))
    if profile.country:
        personal.fields.append(AutofillField(label="Country", value=profile.country))
    if personal.fields:
        sections.append(personal)

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

    if profile.headline:
        sections.append(AutofillSection(title="Professional Headline", fields=[
            AutofillField(label="Headline", value=profile.headline),
        ]))
    if profile.summary:
        sections.append(AutofillSection(title="Summary", fields=[
            AutofillField(label="Professional Summary", value=profile.summary, field_type="textarea"),
        ]))

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
    if hasattr(profile, 'authorized_to_work_in_us') and profile.authorized_to_work_in_us is not None:
        prefs.fields.append(AutofillField(label="Authorized to work", value="Yes" if profile.authorized_to_work_in_us else "No"))
    if hasattr(profile, 'need_visa_sponsorship') and profile.need_visa_sponsorship is not None:
        prefs.fields.append(AutofillField(label="Visa Sponsorship", value="Yes" if profile.need_visa_sponsorship else "No"))
    if hasattr(profile, 'currently_employed') and profile.currently_employed is not None:
        prefs.fields.append(AutofillField(label="Currently Employed", value="Yes" if profile.currently_employed else "No"))
    if profile.notice_period_days:
        prefs.fields.append(AutofillField(label="Notice Period", value=f"{profile.notice_period_days} days"))
    if prefs.fields:
        sections.append(prefs)

    if profile.cover_letter_intro:
        sections.append(AutofillSection(title="Cover Letter", fields=[
            AutofillField(label="Cover Letter", value=profile.cover_letter_intro, field_type="textarea"),
        ]))

    # Demographic / EEO
    eeoc = AutofillSection(title="Equal Employment Opportunity", fields=[])
    if profile.gender:
        eeoc.fields.append(AutofillField(label="Gender", value=profile.gender))
    if profile.hispanic_latino:
        eeoc.fields.append(AutofillField(label="Hispanic/Latino", value=profile.hispanic_latino))
    if profile.veteran_status:
        eeoc.fields.append(AutofillField(label="Veteran Status", value=profile.veteran_status))
    if profile.disability_status:
        eeoc.fields.append(AutofillField(label="Disability Status", value=profile.disability_status))
    if eeoc.fields:
        sections.append(eeoc)

    latest_cv = (
        db.query(CV)
        .filter(CV.user_id == current_user.id)
        .order_by(CV.created_at.desc())
        .first()
    )

    return AutofillProfileData(
        sections=sections,
        resume_url=latest_cv.cloudinary_url if latest_cv else "",
        resume_name=latest_cv.file_name if latest_cv else "",
    )


class AiField(BaseModel):
    label: str
    name: str = ""
    type: str = "text"
    value: str = ""


class AiAutoFillResponse(BaseModel):
    fields: list[AiField]


@router.post("/ai-autofill", response_model=AiAutoFillResponse)
def ai_autofill(
    form_fields: list[AiField],
    current_user: User = Depends(get_current_user),
    service: UserProfileService = Depends(),
    db: Session = Depends(get_db),
):
    """Use AI (Gemini free tier) to match form fields to profile data."""
    settings = get_settings()
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="AI autofill not configured (GEMINI_API_KEY missing)")

    profile = service.get_or_create(current_user.id)
    exp_list = profile.experiences or []
    edu_list = profile.education or []

    # Build profile context for the AI
    parts = [f"First Name: {current_user.first_name or ''}", f"Last Name: {current_user.last_name or ''}"]
    if current_user.email:
        parts.append(f"Email: {current_user.email}")
    if profile.phone:
        parts.append(f"Phone: {profile.phone}")
    if profile.city and profile.country:
        parts.append(f"Location: {profile.city}, {profile.country}")
    elif profile.city:
        parts.append(f"Location: {profile.city}")
    if profile.linkedin_url:
        parts.append(f"LinkedIn: {profile.linkedin_url}")
    if profile.github_url:
        parts.append(f"GitHub: {profile.github_url}")
    if profile.portfolio_url:
        parts.append(f"Portfolio: {profile.portfolio_url}")
    if profile.headline:
        parts.append(f"Headline: {profile.headline}")
    if profile.summary:
        parts.append(f"Professional Summary: {profile.summary}")
    if profile.how_did_you_hear:
        parts.append(f"How did you hear: {profile.how_did_you_hear}")
    if profile.cover_letter_intro:
        parts.append(f"Cover Letter Intro: {profile.cover_letter_intro}")
    if profile.desired_roles:
        parts.append(f"Desired Roles: {', '.join(profile.desired_roles)}")
    if profile.desired_salary_min or profile.desired_salary_max:
        parts.append(f"Desired Salary: {profile.desired_salary_currency} {profile.desired_salary_min or ''}-{profile.desired_salary_max or ''}")
    if profile.gender:
        parts.append(f"Gender: {profile.gender}")
    if profile.hispanic_latino:
        parts.append(f"Hispanic/Latino: {profile.hispanic_latino}")
    if profile.veteran_status:
        parts.append(f"Veteran Status: {profile.veteran_status}")
    if profile.disability_status:
        parts.append(f"Disability Status: {profile.disability_status}")

    for exp in exp_list:
        tech = f" [{', '.join(exp.tech_used or [])}]" if exp.tech_used else ""
        parts.append(f"Work: {exp.title} @ {exp.company}{tech}")
        if exp.description:
            parts.append(f"  Description: {exp.description}")
        if exp.achievements:
            parts.append(f"  Achievements: {'; '.join(exp.achievements)}")

    for edu in edu_list:
        parts.append(f"Education: {edu.degree} in {edu.field_of_study or ''} @ {edu.school}")

    if profile.custom_answers:
        for q, a in profile.custom_answers.items():
            parts.append(f"Q: {q} → A: {a}")

    profile_text = "\n".join(parts)

    fields_text = "\n".join(
        f"- label: \"{f.label}\" name: \"{f.name}\" type: \"{f.type}\""
        for f in form_fields
    )

    prompt = f"""You are an autofill assistant. Given a user's profile and a list of form fields from a job application page, match each field to the most appropriate value from the profile.

Rules:
- For standard fields (first name, last name, email, phone, location, linkedin, github, portfolio, headline, salary, gender, veteran, hispanic, disability, how hear), use the exact profile value.
- For "Preferred First Name" or similar, use the first name.
- For "Where are you located?" use city + country from profile.
- For "How did you hear about this opportunity?" use the profile's "How did you hear" value.
- For custom questions like "Why do you want to work here?", "What is one of the hardest technical problems...", generate a short professional answer (2-3 sentences) based on the user's work experience, achievements, and summary. Be specific and use details from their profile.

Return ONLY a JSON array of objects with "label", "name", and "value" fields. Do not include fields that cannot be matched.

User Profile:
{profile_text}

Form Fields:
{fields_text}

JSON response:"""

    import httpx
    gemini_error = None
    try:
        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.gemini_api_key}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048},
            },
            timeout=30,
        )
        if not resp.ok:
            error_body = resp.text[:500]
            raise Exception(f"HTTP {resp.status}: {error_body}")
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        import json
        result = json.loads(text)
        return AiAutoFillResponse(fields=[AiField(**f) for f in result])
    except Exception as e:
        gemini_error = str(e)

    # Fallback: rule-based matching if Gemini fails
    def norm(s: str) -> str:
        return "".join(c for c in s.lower() if c.isalnum())

    profile_map: dict[str, str] = {}
    if current_user.first_name:
        profile_map["firstname"] = current_user.first_name
    if current_user.last_name:
        profile_map["lastname"] = current_user.last_name
    if current_user.email:
        profile_map["email"] = current_user.email
    if profile.phone:
        profile_map["phone"] = profile.phone
    if profile.city:
        profile_map["city"] = profile.city
    if profile.state:
        profile_map["state"] = profile.state
    if profile.postal_code:
        profile_map["postalcode"] = profile.postal_code
    if profile.country:
        profile_map["country"] = profile.country
    if profile.linkedin_url:
        profile_map["linkedinurl"] = profile.linkedin_url
    if profile.github_url:
        profile_map["githuburl"] = profile.github_url
    if profile.portfolio_url:
        profile_map["portfoliourl"] = profile.portfolio_url
    if profile.website:
        profile_map["website"] = profile.website
    if profile.headline:
        profile_map["headline"] = profile.headline
    if profile.summary:
        profile_map["professionalsummary"] = profile.summary
    if profile.how_did_you_hear:
        profile_map["howdidyouhear"] = profile.how_did_you_hear
    if profile.gender:
        profile_map["gender"] = profile.gender
    if profile.hispanic_latino:
        profile_map["hispaniclatino"] = profile.hispanic_latino
    if profile.veteran_status:
        profile_map["veteranstatus"] = profile.veteran_status
    if profile.disability_status:
        profile_map["disabilitystatus"] = profile.disability_status
    if profile.cover_letter_intro:
        profile_map["coverletter"] = profile.cover_letter_intro
    # Work experience fields (from first entry)
    first_exp = (profile.experiences or [None])[0]
    if first_exp:
        profile_map["company"] = first_exp.company
        profile_map["jobtitle"] = first_exp.title
        if first_exp.location:
            profile_map["explocation"] = first_exp.location
        if first_exp.start_date:
            profile_map["startdate"] = first_exp.start_date
        if first_exp.end_date and not first_exp.currently_working:
            profile_map["enddate"] = first_exp.end_date
        if first_exp.description:
            profile_map["roledescription"] = first_exp.description
        if first_exp.tech_used:
            profile_map["techused"] = ", ".join(first_exp.tech_used)
    # Education fields (from first entry)
    first_edu = (profile.education or [None])[0]
    if first_edu:
        profile_map["school"] = first_edu.school
        profile_map["degree"] = first_edu.degree
        if first_edu.field_of_study:
            profile_map["fieldofstudy"] = first_edu.field_of_study
        if first_edu.start_date:
            profile_map["edustartdate"] = first_edu.start_date
        if first_edu.end_date and not first_edu.currently_studying:
            profile_map["eduenddate"] = first_edu.end_date
        if first_edu.gpa:
            profile_map["gpa"] = first_edu.gpa

    field_keywords: list[tuple[str, list[str]]] = [
        ("firstname", ["firstname", "first name", "givenname", "forename"]),
        ("lastname", ["lastname", "last name", "surname", "familyname"]),
        ("email", ["email", "e-mail", "mail"]),
        ("phone", ["phone", "telephone", "mobile", "phonenumber", "cell", "contactnumber"]),
        ("linkedinurl", ["linkedin", "linked in"]),
        ("githuburl", ["github", "git hub"]),
        ("portfoliourl", ["portfolio", "portfolio url"]),
        ("website", ["website", "personal website", "homepage", "url"]),
        ("city", ["city", "town"]),
        ("state", ["state", "province", "region"]),
        ("country", ["country", "nation"]),
        ("postalcode", ["postalcode", "postal code", "zip", "zipcode"]),
        ("headline", ["headline", "professional title", "current title"]),
        ("professionalsummary", ["summary", "professionalsummary", "bio", "about me", "professional summary"]),
        ("howdidyouhear", ["howdidyouhear", "how did you hear", "source", "referral", "found us"]),
        ("gender", ["gender", "sex"]),
        ("hispaniclatino", ["hispanic", "latino", "hispanic latino"]),
        ("veteranstatus", ["veteran", "military", "armed forces", "veteran status"]),
        ("disabilitystatus", ["disability", "disabled", "disability status"]),
        ("coverletter", ["coverletter", "cover letter", "message", "additional info", "why you", "why this company", "introduction"]),
        ("company", ["company", "employer", "organization", "current company", "current employer"]),
        ("jobtitle", ["position", "job title", "role", "title", "job position", "jobtitle"]),
        ("explocation", ["location", "where located", "located", "where are you located", "work location", "job location"]),
        ("startdate", ["start date", "startdate", "from", "start"]),
        ("enddate", ["end date", "enddate", "to", "end", "finish"]),
        ("roledescription", ["description", "role description", "job description", "responsibilities"]),
        ("techused", ["technology", "technologies", "tech used", "skills", "tools"]),
        ("school", ["school", "university", "college", "institution", "educational institution"]),
        ("degree", ["degree", "qualification", "education level", "education"]),
        ("fieldofstudy", ["field of study", "fieldofstudy", "major", "area of study", "discipline", "subject"]),
        ("edustartdate", ["start date", "startdate", "from", "start"]),
        ("eduenddate", ["end date", "enddate", "to", "end", "finish"]),
        ("gpa", ["gpa", "grade point average", "grade point", "overall result"]),
    ]

    fallback_fields: list[AiField] = []
    for ff in form_fields:
        fn = norm(ff.label)
        nn = norm(ff.name)
        matched_key = None
        for pk, kws in field_keywords:
            if any(kw in fn for kw in kws) or any(kw in nn for kw in kws):
                matched_key = pk
                break
        if matched_key and matched_key in profile_map:
            fallback_fields.append(AiField(label=ff.label, name=ff.name, value=profile_map[matched_key]))

    detail = f"AI unavailable ({gemini_error}). Filled {len(fallback_fields)} fields via rule matching."
    return AiAutoFillResponse(fields=fallback_fields)
