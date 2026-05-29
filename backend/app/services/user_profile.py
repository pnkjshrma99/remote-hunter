"""Service layer for extended user profile."""

from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_profile import UserProfile, WorkExperience, Education
from app.schemas.user_profile import (
    UserProfileCreate,
    UserProfileUpdate,
    WorkExperienceCreate,
    EducationCreate,
)


class UserProfileService:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get_or_create(self, user_id: int) -> UserProfile:
        profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
        return profile

    def get(self, user_id: int) -> Optional[UserProfile]:
        return self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    def update(self, user_id: int, data: UserProfileUpdate) -> UserProfile:
        profile = self.get_or_create(user_id)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(profile, key, value)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def add_experience(self, user_id: int, data: WorkExperienceCreate) -> WorkExperience:
        profile = self.get_or_create(user_id)
        exp = WorkExperience(profile_id=profile.id, **data.model_dump())
        self.db.add(exp)
        self.db.commit()
        self.db.refresh(exp)
        return exp

    def update_experience(self, experience_id: int, user_id: int, data: WorkExperienceCreate) -> Optional[WorkExperience]:
        exp = self.db.query(WorkExperience).join(UserProfile).filter(
            WorkExperience.id == experience_id,
            UserProfile.user_id == user_id,
        ).first()
        if not exp:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(exp, key, value)
        self.db.commit()
        self.db.refresh(exp)
        return exp

    def delete_experience(self, experience_id: int, user_id: int) -> bool:
        exp = self.db.query(WorkExperience).join(UserProfile).filter(
            WorkExperience.id == experience_id,
            UserProfile.user_id == user_id,
        ).first()
        if not exp:
            return False
        self.db.delete(exp)
        self.db.commit()
        return True

    def add_education(self, user_id: int, data: EducationCreate) -> Education:
        profile = self.get_or_create(user_id)
        edu = Education(profile_id=profile.id, **data.model_dump())
        self.db.add(edu)
        self.db.commit()
        self.db.refresh(edu)
        return edu

    def update_education(self, education_id: int, user_id: int, data: EducationCreate) -> Optional[Education]:
        edu = self.db.query(Education).join(UserProfile).filter(
            Education.id == education_id,
            UserProfile.user_id == user_id,
        ).first()
        if not edu:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(edu, key, value)
        self.db.commit()
        self.db.refresh(edu)
        return edu

    def delete_education(self, education_id: int, user_id: int) -> bool:
        edu = self.db.query(Education).join(UserProfile).filter(
            Education.id == education_id,
            UserProfile.user_id == user_id,
        ).first()
        if not edu:
            return False
        self.db.delete(edu)
        self.db.commit()
        return True
