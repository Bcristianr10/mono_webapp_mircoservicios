from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CourseOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    instructor_id: int
    capacity: int
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    capacity: int = 30


class CourseUpdate(BaseModel):
    title: str
    description: Optional[str] = None
    capacity: int
