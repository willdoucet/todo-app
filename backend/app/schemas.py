import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from datetime import datetime, date as _Date
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


_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _validate_hex_color(v: Optional[str]) -> Optional[str]:
    if v is not None and not _HEX_COLOR_RE.match(v):
        raise ValueError("Color must be a valid hex color (e.g. #FF0000)")
    return v


class FamilyMemberBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    photo_url: Optional[str] = None
    color: Optional[str] = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v):
        return _validate_hex_color(v)


class FamilyMemberCreate(FamilyMemberBase):
    pass


class FamilyMemberUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    photo_url: Optional[str] = None
    color: Optional[str] = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v):
        return _validate_hex_color(v)


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
    priority: int = Field(default=0, ge=0, le=9)
    list_id: int = Field(..., ge=1)
    parent_id: Optional[int] = None
    section_id: Optional[int] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    due_date: Optional[datetime] = Field(None)
    completed: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=9)
    assigned_to: Optional[int] = Field(None, ge=1, le=1000000)
    list_id: Optional[int] = Field(None, ge=1)
    parent_id: Optional[int] = None
    section_id: Optional[int] = None
    completed_at: Optional[datetime] = None


class Task(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_synced: bool = False
    children: TypingList["Task"] = []
    completed_at: Optional[datetime] = None
    external_id: Optional[str] = None
    sync_status: Optional[str] = None
    calendar_integration_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    family_member: FamilyMember

    @model_validator(mode="before")
    @classmethod
    def compute_is_synced(cls, data):
        """Derive is_synced from calendar_integration_id presence."""
        if hasattr(data, "calendar_integration_id"):
            # ORM model
            data.__dict__["is_synced"] = data.calendar_integration_id is not None
        elif isinstance(data, dict):
            data["is_synced"] = data.get("calendar_integration_id") is not None
        return data


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
    completion_date: _Date
    category: str


class ResponsibilityCompletionCreate(BaseModel):
    completion_date: _Date


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


# =============================================================================
# Section Schemas
# =============================================================================


class SectionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., min_length=1, max_length=100)


class SectionCreate(SectionBase):
    pass


class SectionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    sort_order: Optional[int] = Field(None, ge=0)


class Section(SectionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    list_id: int
    sort_order: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None


class List(ListBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_synced: bool = False
    sections: TypingList[Section] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def compute_is_synced(cls, data):
        """Derive is_synced from calendar_integration_id presence."""
        if hasattr(data, "calendar_integration_id"):
            data.__dict__["is_synced"] = data.calendar_integration_id is not None
        elif isinstance(data, dict):
            data["is_synced"] = data.get("calendar_integration_id") is not None
        return data


# =============================================================================
# Recipe Schemas
# =============================================================================


class Ingredient(BaseModel):
    name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None  # Predefined unit (lb, oz, g, cup, tbsp, etc.) or None for pantry staples
    category: str = "Other"

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v):
        if v is None:
            return v
        from app.constants.units import VALID_UNITS
        if v not in VALID_UNITS:
            raise ValueError(f"Invalid unit '{v}'. Must be one of: {', '.join(VALID_UNITS)}")
        return v


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
# MealSlotType Schemas
# =============================================================================


class MealSlotTypeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., min_length=1, max_length=100)
    sort_order: int = Field(default=0, ge=0)
    color: Optional[str] = Field(None, max_length=7)  # Hex color
    icon: Optional[str] = Field(None, max_length=10)  # Emoji
    is_active: bool = True
    default_participants: Optional[TypingList[int]] = None  # Family member IDs; [] = everyone


class MealSlotTypeCreate(MealSlotTypeBase):
    pass


class MealSlotTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    sort_order: Optional[int] = Field(None, ge=0)
    color: Optional[str] = Field(None, max_length=7)
    icon: Optional[str] = Field(None, max_length=10)
    is_active: Optional[bool] = None
    default_participants: Optional[TypingList[int]] = None


class MealSlotType(MealSlotTypeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_default: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


# =============================================================================
# FoodItem Schemas
# =============================================================================


class FoodItemBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., min_length=1, max_length=200)
    emoji: Optional[str] = Field(None, max_length=10)
    category: Optional[str] = Field(None, max_length=50)  # fruit, dairy, grain, protein, vegetable
    is_favorite: bool = False


class FoodItemCreate(FoodItemBase):
    pass


class FoodItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    emoji: Optional[str] = Field(None, max_length=10)
    category: Optional[str] = Field(None, max_length=50)
    is_favorite: Optional[bool] = None


class FoodItem(FoodItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# =============================================================================
# MealEntry Schemas (replaces MealPlan)
# =============================================================================


class MealItemType(str, Enum):
    RECIPE = "recipe"
    FOOD_ITEM = "food_item"
    CUSTOM = "custom"


class ShoppingSyncStatus(str, Enum):
    SYNCED = "synced"
    PENDING = "pending"
    FAILED = "failed"


class FamilyMemberBrief(BaseModel):
    """Minimal family member info for meal entry participant lists."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: Optional[str] = None
    photo_url: Optional[str] = None


class MealEntryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: _Date
    meal_slot_type_id: int = Field(..., ge=1)
    recipe_id: Optional[int] = Field(None, ge=1)
    food_item_id: Optional[int] = Field(None, ge=1)
    custom_meal_name: Optional[str] = Field(None, max_length=200)
    item_type: MealItemType
    servings: Optional[int] = Field(None, ge=1)
    was_cooked: bool = False
    notes: Optional[str] = Field(None, max_length=500)
    sort_order: int = Field(default=0, ge=0)


class MealEntryCreate(MealEntryBase):
    participant_ids: Optional[TypingList[int]] = None  # Family member IDs; None = use slot defaults


class MealEntryUpdate(BaseModel):
    date: Optional[_Date] = None
    meal_slot_type_id: Optional[int] = Field(None, ge=1)
    recipe_id: Optional[int] = Field(None, ge=1)
    food_item_id: Optional[int] = Field(None, ge=1)
    custom_meal_name: Optional[str] = Field(None, max_length=200)
    item_type: Optional[MealItemType] = None
    was_cooked: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=500)
    sort_order: Optional[int] = Field(None, ge=0)
    participant_ids: Optional[TypingList[int]] = None


class MealEntry(MealEntryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipe: Optional[Recipe] = None
    food_item: Optional[FoodItem] = None
    meal_slot_type: Optional[MealSlotType] = None
    participants: Optional[TypingList[FamilyMemberBrief]] = None
    shopping_sync_status: Optional[ShoppingSyncStatus] = None
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
    date: _Date
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    all_day: bool = False
    assigned_to: Optional[int] = Field(None, ge=1)
    timezone: Optional[str] = None

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time_format(cls, v):
        if v is not None and not _TIME_RE.match(v):
            raise ValueError("Time must be in HH:MM format")
        return v


class CalendarEventCreate(CalendarEventBase):
    source: CalendarEventSource = CalendarEventSource.MANUAL
    external_id: Optional[str] = None
    calendar_id: Optional[int] = None


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    date: Optional[_Date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    all_day: Optional[bool] = None
    assigned_to: Optional[int] = Field(None, ge=1)
    calendar_id: Optional[int] = None

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time_format(cls, v):
        if v is not None and not _TIME_RE.match(v):
            raise ValueError("Time must be in HH:MM format")
        return v


class CalendarResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    calendar_integration_id: int
    calendar_url: str
    name: str
    color: Optional[str] = None
    is_todo: Optional[bool] = False
    family_member_name: Optional[str] = None
    integration_email: Optional[str] = None


class CalendarEvent(CalendarEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: CalendarEventSource
    external_id: Optional[str] = None
    family_member: Optional[FamilyMember] = None
    sync_status: Optional[str] = None
    calendar_integration_id: Optional[int] = None
    calendar_id: Optional[int] = None
    calendar: Optional[CalendarResponse] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# =============================================================================
# CalendarIntegration Schemas
# =============================================================================


class IntegrationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ERROR = "ERROR"
    SYNCING = "SYNCING"
    DISCONNECTED = "DISCONNECTED"


class CalendarIntegrationCreate(BaseModel):
    family_member_id: int = Field(..., ge=1)
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)  # Plain text — encrypted before storage
    selected_calendars: Optional[TypingList[str]] = None
    calendar_details: Optional[TypingList[dict]] = None  # [{url, name, color}] from validate step


class CalendarIntegrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    family_member_id: int
    provider: str
    email: str
    # NOTE: password is NEVER returned
    status: IntegrationStatus
    last_sync_at: Optional[datetime] = None
    last_error: Optional[str] = None
    reminders_status: Optional[IntegrationStatus] = None
    reminders_last_error: Optional[str] = None
    reminders_last_sync_at: Optional[datetime] = None
    sync_range_past_days: int
    sync_range_future_days: int
    selected_calendars: Optional[TypingList[str]] = None
    calendars: Optional[TypingList[CalendarResponse]] = None
    reminder_lists: Optional[TypingList[CalendarResponse]] = None
    family_member: FamilyMember
    created_at: datetime
    updated_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def split_calendar_types(cls, data):
        """Separate calendars into event calendars and reminder lists."""
        if hasattr(data, "calendars") and data.calendars:
            all_cals = data.calendars
            event_cals = [c for c in all_cals if not bool(getattr(c, "is_todo", False))]
            reminder_cals = [c for c in all_cals if bool(getattr(c, "is_todo", False))]
            data.__dict__["calendars"] = event_cals
            data.__dict__["reminder_lists"] = reminder_cals
        return data


class ICloudCalendarInfo(BaseModel):
    """Returned when listing available calendars from an iCloud account."""
    url: str
    name: str
    color: Optional[str] = None
    event_count: Optional[int] = None
    already_synced_by: Optional[str] = None


class ICloudReminderListInfo(BaseModel):
    """Returned when listing available reminder lists from an iCloud account."""
    url: str
    name: str
    color: Optional[str] = None
    task_count: Optional[int] = None
    already_synced_by: Optional[str] = None


class RemindersValidatePayload(BaseModel):
    integration_id: int = Field(..., ge=1)


class RemindersConnectPayload(BaseModel):
    integration_id: int = Field(..., ge=1)
    selected_lists: TypingList[str] = Field(..., min_length=1)


# =============================================================================
# AppSettings Schemas
# =============================================================================


class AppSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timezone: str
    week_start_day: str = "monday"
    measurement_system: str = "imperial"
    mealboard_shopping_list_id: Optional[int] = None


class AppSettingsUpdate(BaseModel):
    timezone: Optional[str] = None
    week_start_day: Optional[str] = None
    measurement_system: Optional[str] = None
    mealboard_shopping_list_id: Optional[int] = None

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v):
        if v is not None:
            from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
            try:
                ZoneInfo(v)
            except (ZoneInfoNotFoundError, KeyError):
                raise ValueError(f"Invalid IANA timezone: {v}")
        return v

    @field_validator("week_start_day")
    @classmethod
    def validate_week_start_day(cls, v):
        if v is not None and v not in ("monday", "sunday"):
            raise ValueError("week_start_day must be 'monday' or 'sunday'")
        return v

    @field_validator("measurement_system")
    @classmethod
    def validate_measurement_system(cls, v):
        if v is not None and v not in ("imperial", "metric"):
            raise ValueError("measurement_system must be 'imperial' or 'metric'")
        return v
