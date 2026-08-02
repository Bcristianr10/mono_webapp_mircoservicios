from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class EnrollmentOut(BaseModel):
    id: int
    user_id: int
    course_id: int
    status: str
    enrolled_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EnrollmentCreate(BaseModel):
    course_id: int
