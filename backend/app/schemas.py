from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class FamilyMemberBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


class FamilyMemberCreate(FamilyMemberBase):
    pass


class FamilyMemberUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)


class FamilyMember(FamilyMemberBase):
    id: int
    is_system: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    due_date: Optional[datetime] = Field(None)
    completed: bool = False
    assigned_to: int = Field(..., ge=1, le=1000000)
    important: bool = False

    class Config:
        from_attributes = True


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    due_date: Optional[datetime] = Field(None)
    completed: Optional[bool] = None
    important: Optional[bool] = None
    assigned_to: Optional[int] = Field(None, ge=1, le=1000000)


class Task(TaskBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    family_member: FamilyMember

    class Config:
        from_attributes = True
