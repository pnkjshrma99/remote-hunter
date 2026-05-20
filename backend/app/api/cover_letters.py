from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cover_letter import CoverLetterTemplate
from app.schemas.cover_letter import (
    CoverLetterCreate,
    CoverLetterResponse,
    CoverLetterUpdate,
)

router = APIRouter(prefix="/cover-letters", tags=["cover letters"])


@router.get("", response_model=list[CoverLetterResponse])
def list_templates(db: Session = Depends(get_db)):
    stmt = select(CoverLetterTemplate).order_by(CoverLetterTemplate.updated_at.desc())
    return list(db.scalars(stmt))


@router.post("", response_model=CoverLetterResponse)
def create_template(payload: CoverLetterCreate, db: Session = Depends(get_db)):
    template = CoverLetterTemplate(**payload.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.patch("/{template_id}", response_model=CoverLetterResponse)
def update_template(
    template_id: int,
    payload: CoverLetterUpdate,
    db: Session = Depends(get_db),
):
    template = db.get(CoverLetterTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    template = db.get(CoverLetterTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(template)
    db.commit()
    return {"status": "deleted"}
