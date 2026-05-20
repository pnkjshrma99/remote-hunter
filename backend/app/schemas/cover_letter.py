from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CoverLetterBase(BaseModel):
    name: str
    content: str
    company_type: Optional[str] = None


class CoverLetterCreate(CoverLetterBase):
    pass


class CoverLetterUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    company_type: Optional[str] = None


class CoverLetterResponse(CoverLetterBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
