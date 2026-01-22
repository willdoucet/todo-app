from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from .models import AssignedTo


class TodoBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    due_date: Optional[datetime] = Field(None)
    completed: bool = False
    assigned_to: AssignedTo = Field(default=AssignedTo.ALL)
    important: bool = False


class TodoCreate(TodoBase):
    pass


class TodoUpdate(TodoBase):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    due_date: Optional[datetime] = Field(None)
    completed: Optional[bool] = None
    important: Optional[bool] = None
    assigned_to: Optional[AssignedTo] = None

    class Config:
        from_attributes = True


class Todo(TodoBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
