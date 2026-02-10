import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from datetime import datetime, date
from typing import Optional, List as TypingList
from enum import Enum


class ResponsibilityCategory(str, Enum):
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    EVENING = "EVENING"
    CHORE = "CHORE"


class MealCategory(str, Enum):
    BREAKFAST = "BREAKFAST"
    LUNCH = "LUNCH"
    DINNER = "DINNER"


class FamilyMemberBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    photo_url: Optional[str] = None
    color: Optional[str] = None


class FamilyMemberCreate(FamilyMemberBase):
    pass


class FamilyMemberUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    photo_url: Optional[str] = None
    color: Optional[str] = None


class FamilyMember(FamilyMemberBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_system: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class TaskBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    due_date: Optional[datetime] = Field(None)
    completed: bool = False
    assigned_to: int = Field(..., ge=1, le=1000000)
    important: bool = False
    list_id: int = Field(..., ge=1)


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
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    family_member: FamilyMember


class ResponsibilityBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    categories: TypingList[ResponsibilityCategory] = Field(..., min_length=1)
    assigned_to: int = Field(..., ge=1)
    frequency: TypingList[str] = Field(..., min_length=1)
    icon_url: Optional[str] = None


class ResponsibilityCreate(ResponsibilityBase):
    pass


class ResponsibilityUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    categories: Optional[TypingList[ResponsibilityCategory]] = None
    assigned_to: Optional[int] = Field(None, ge=1)
    frequency: Optional[TypingList[str]] = None
    icon_url: Optional[str] = None


class Responsibility(ResponsibilityBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    family_member: FamilyMember


class ResponsibilityCompletionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    responsibility_id: int = Field(..., ge=1)
    family_member_id: int = Field(..., ge=1)
    completion_date: date
    category: str


class ResponsibilityCompletionCreate(BaseModel):
    completion_date: date


class ResponsibilityCompletion(ResponsibilityCompletionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class ListBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., min_length=1, max_length=100)
    color: Optional[str] = Field(None, min_length=1, max_length=7)
    icon: Optional[str] = Field(None, min_length=1, max_length=100)


class ListCreate(ListBase):
    pass


class ListUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, min_length=1, max_length=7)
    icon: Optional[str] = Field(None, min_length=1, max_length=100)


class List(ListBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# =============================================================================
# Recipe Schemas
# =============================================================================


class Ingredient(BaseModel):
    name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    category: str = "Other"


class RecipeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    ingredients: Optional[TypingList[Ingredient]] = None
    instructions: str = Field(..., min_length=1)
    prep_time_minutes: Optional[int] = Field(None, ge=0)
    cook_time_minutes: Optional[int] = Field(None, ge=0)
    servings: int = Field(default=4, ge=1)
    image_url: Optional[str] = None
    is_favorite: bool = False
    tags: Optional[TypingList[str]] = None


class RecipeCreate(RecipeBase):
    pass


class RecipeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    ingredients: Optional[TypingList[Ingredient]] = None
    instructions: Optional[str] = Field(None, min_length=1)
    prep_time_minutes: Optional[int] = Field(None, ge=0)
    cook_time_minutes: Optional[int] = Field(None, ge=0)
    servings: Optional[int] = Field(None, ge=1)
    image_url: Optional[str] = None
    is_favorite: Optional[bool] = None
    tags: Optional[TypingList[str]] = None


class Recipe(RecipeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# =============================================================================
# MealPlan Schemas
# =============================================================================


class MealPlanBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    category: MealCategory
    recipe_id: Optional[int] = Field(None, ge=1)
    custom_meal_name: Optional[str] = Field(None, max_length=200)
    was_cooked: bool = False
    notes: Optional[str] = Field(None, max_length=500)


class MealPlanCreate(MealPlanBase):
    pass


class MealPlanUpdate(BaseModel):
    date: Optional[date] = None
    category: Optional[MealCategory] = None
    recipe_id: Optional[int] = Field(None, ge=1)
    custom_meal_name: Optional[str] = Field(None, max_length=200)
    was_cooked: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=500)


class MealPlan(MealPlanBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipe: Optional[Recipe] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# =============================================================================
# CalendarEvent Schemas
# =============================================================================

_TIME_RE = re.compile(r"^\d{2}:\d{2}$")


class CalendarEventSource(str, Enum):
    MANUAL = "MANUAL"
    ICLOUD = "ICLOUD"
    GOOGLE = "GOOGLE"


class CalendarEventBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    date: date
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    all_day: bool = False
    assigned_to: Optional[int] = Field(None, ge=1)

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time_format(cls, v):
        if v is not None and not _TIME_RE.match(v):
            raise ValueError("Time must be in HH:MM format")
        return v

    @model_validator(mode="after")
    def validate_end_after_start(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class CalendarEventCreate(CalendarEventBase):
    source: CalendarEventSource = CalendarEventSource.MANUAL
    external_id: Optional[str] = None


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    all_day: Optional[bool] = None
    assigned_to: Optional[int] = Field(None, ge=1)

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time_format(cls, v):
        if v is not None and not _TIME_RE.match(v):
            raise ValueError("Time must be in HH:MM format")
        return v

    @model_validator(mode="after")
    def validate_end_after_start(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class CalendarEvent(CalendarEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: CalendarEventSource
    external_id: Optional[str] = None
    family_member: Optional[FamilyMember] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
