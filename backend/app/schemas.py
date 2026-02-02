from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List
from enum import Enum


class ResponsibilityCategory(str, Enum):
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    EVENING = "EVENING"
    CHORE = "CHORE"


class FamilyMemberBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    photo_url: Optional[str] = None


class FamilyMemberCreate(FamilyMemberBase):
    pass


class FamilyMemberUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    photo_url: Optional[str] = None


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
    list_id: int = Field(..., ge=1)

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
    list_id: Optional[int] = Field(None, ge=1)


class Task(TaskBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    family_member: FamilyMember

    class Config:
        from_attributes = True


class ResponsibilityBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    category: ResponsibilityCategory
    assigned_to: int = Field(..., ge=1)
    frequency: List[str] = Field(..., min_length=1)
    icon_url: Optional[str] = None

    class Config:
        from_attributes = True


class ResponsibilityCreate(ResponsibilityBase):
    pass


class ResponsibilityUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    category: Optional[ResponsibilityCategory] = None
    assigned_to: Optional[int] = Field(None, ge=1)
    frequency: Optional[List[str]] = None
    icon_url: Optional[str] = None


class Responsibility(ResponsibilityBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    family_member: FamilyMember

    class Config:
        from_attributes = True


class ResponsibilityCompletionBase(BaseModel):
    responsibility_id: int = Field(..., ge=1)
    family_member_id: int = Field(..., ge=1)
    completion_date: date

    class Config:
        from_attributes = True


class ResponsibilityCompletionCreate(BaseModel):
    completion_date: date


class ResponsibilityCompletion(ResponsibilityCompletionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ListBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: Optional[str] = Field(None, min_length=1, max_length=7)
    icon: Optional[str] = Field(None, min_length=1, max_length=100)

    class Config:
        from_attributes = True


class ListCreate(ListBase):
    pass


class ListUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, min_length=1, max_length=7)
    icon: Optional[str] = Field(None, min_length=1, max_length=100)


class List(ListBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
