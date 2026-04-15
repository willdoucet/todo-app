from sqlalchemy import (
    CheckConstraint,
    Column,
    Index,
    Integer,
    Float,
    Numeric,
    String,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    ARRAY,
    JSON,
    Text,
    Table,
    func,
    text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, declarative_base
from enum import Enum as PyEnum

Base = declarative_base()


class ResponsibilityCategory(PyEnum):
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    EVENING = "EVENING"
    CHORE = "CHORE"


class MealCategory(PyEnum):
    """Legacy enum — kept for migration compatibility only. Do not use in new code."""
    BREAKFAST = "BREAKFAST"
    LUNCH = "LUNCH"
    DINNER = "DINNER"


class ShoppingSyncStatus(PyEnum):
    SYNCED = "synced"
    PENDING = "pending"
    FAILED = "failed"
    SKIPPED = "skipped"


class CalendarEventSource(PyEnum):
    MANUAL = "MANUAL"
    ICLOUD = "ICLOUD"
    GOOGLE = "GOOGLE"


class IntegrationStatus(PyEnum):
    ACTIVE = "ACTIVE"
    ERROR = "ERROR"
    SYNCING = "SYNCING"
    DISCONNECTED = "DISCONNECTED"


class FamilyMember(Base):
    __tablename__ = "family_members"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    photo_url = Column(String, nullable=True)  # Path to uploaded photo
    color = Column(String, nullable=True)  # Hex color for calendar display

    tasks = relationship("Task", back_populates="family_member")
    responsibilities = relationship("Responsibility", back_populates="family_member")
    calendar_integrations = relationship("CalendarIntegration", back_populates="family_member")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    due_date = Column(DateTime, nullable=True)
    completed = Column(Boolean, default=False)
    assigned_to = Column(Integer, ForeignKey("family_members.id"), nullable=False)
    family_member = relationship("FamilyMember", back_populates="tasks")
    priority = Column(Integer, default=0, nullable=False)  # 0=none, 1=high, 5=medium, 9=low
    list_id = Column(Integer, ForeignKey("lists.id"), nullable=False)
    list = relationship("List", back_populates="tasks")
    parent_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    children = relationship("Task", back_populates="parent")
    parent = relationship("Task", back_populates="children", remote_side="Task.id")
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True)
    section = relationship("Section", back_populates="tasks")
    sort_order = Column(Integer, default=0, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    # Sync metadata (for iCloud Reminders)
    external_id = Column(String, nullable=True)
    etag = Column(String, nullable=True)
    last_modified_remote = Column(DateTime, nullable=True)
    sync_status = Column(String, nullable=True)  # SYNCED, PENDING_PUSH
    calendar_integration_id = Column(
        Integer,
        ForeignKey("calendar_integrations.id", ondelete="SET NULL"),
        nullable=True,
    )
    integration = relationship("CalendarIntegration", back_populates="synced_tasks")
    # Mealboard shopping sync fields (nullable — only for auto-generated shopping items)
    source_meals = Column(JSON, nullable=True)  # [{meal_entry_id, source_kind, ...}]
    aggregation_key_name = Column(String, nullable=True)  # Canonical normalized name
    aggregation_unit_group = Column(String, nullable=True)  # "weight", "volume", "count", "none"
    aggregation_source = Column(String, nullable=True)  # "mealboard_auto" or NULL for manual
    aggregation_unit = Column(String, nullable=True)  # Specific unit for bucket identity (e.g. "each", "lb")
    aggregation_base_unit = Column(String, nullable=True)  # Base unit (g, ml, or same as aggregation_unit)
    aggregation_base_quantity = Column(Float, nullable=True)  # Summed quantity in base unit
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "external_id",
            "calendar_integration_id",
            name="uq_task_external_integration",
        ),
        UniqueConstraint(
            "list_id",
            "aggregation_source",
            "aggregation_key_name",
            "aggregation_unit",
            name="uq_task_ingredient_aggregate",
        ),
    )


class Responsibility(Base):
    __tablename__ = "responsibilities"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    categories = Column(ARRAY(String), nullable=False)  # e.g. ["MORNING", "EVENING"]
    assigned_to = Column(Integer, ForeignKey("family_members.id"), nullable=False)
    frequency = Column(ARRAY(String), nullable=False)
    icon_url = Column(String, nullable=True)  # Path to icon/image
    description = Column(String, nullable=True)  # Optional description
    family_member = relationship("FamilyMember", back_populates="responsibilities")
    completions = relationship(
        "ResponsibilityCompletion",
        back_populates="responsibility",
        cascade="all, delete-orphan",
    )
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)


class ResponsibilityCompletion(Base):
    __tablename__ = "responsibility_completions"

    id = Column(Integer, primary_key=True, index=True)
    responsibility_id = Column(
        Integer, ForeignKey("responsibilities.id"), nullable=False
    )
    family_member_id = Column(Integer, ForeignKey("family_members.id"), nullable=False)
    completion_date = Column(Date, nullable=False)
    category = Column(String, nullable=False)  # Which category was completed

    responsibility = relationship("Responsibility", back_populates="completions")
    family_member = relationship("FamilyMember")

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "responsibility_id",
            "completion_date",
            "category",
            name="uq_responsibility_completion_date_category",
        ),
    )


class Item(Base):
    """Unified Item model — replaces Recipe + FoodItem as of the item-model refactor.

    An Item is either a recipe or a food_item, discriminated by `item_type`. Recipe-
    only fields live in `recipe_details`, food-item-only fields in `food_item_details`.
    Both detail tables have a PK FK on `items.id` with ON DELETE CASCADE.

    Icon XOR: an item can have `icon_emoji` OR `icon_url`, never both (enforced by the
    `items_icon_xor_check` DB check constraint).

    Soft-delete: items are deleted by setting `deleted_at`; the row remains in the table
    and is hidden via `WHERE deleted_at IS NULL` in the `active_items_stmt()` query
    builder in `crud_items.py`. See Expansion B for the full soft-delete + undo flow.
    """
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    item_type = Column(Text, nullable=False)  # 'recipe' | 'food_item' (DB CHECK enforces)
    icon_emoji = Column(Text, nullable=True)
    icon_url = Column(Text, nullable=True)
    tags = Column(JSONB, nullable=False, server_default="[]")  # list[str]
    is_favorite = Column(Boolean, nullable=False, default=False, server_default="false")
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Eager-load detail relationships via selectinload to avoid N+1 on list queries.
    # Adversarial review #3 + #7: default lazy loading produces N+1 on any query that
    # touches .recipe_detail or .food_item_detail across a result set.
    recipe_detail = relationship(
        "RecipeDetail",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
        back_populates="item",
    )
    food_item_detail = relationship(
        "FoodItemDetail",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
        back_populates="item",
    )
    # Back-reference only — DO NOT read `item.meal_entries` from UI/CRUD code.
    # It loads ALL rows including soft-hidden ones. Use `visible_meal_entries_stmt()`
    # in `crud_meal_entries.py` instead. See Eng Review #3 Issue 6.
    meal_entries = relationship(
        "MealEntry", back_populates="item", lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint(
            "item_type IN ('recipe', 'food_item')",
            name="items_item_type_check",
        ),
        CheckConstraint(
            "NOT (icon_emoji IS NOT NULL AND icon_url IS NOT NULL)",
            name="items_icon_xor_check",
        ),
        Index("items_item_type_idx", "item_type"),
        Index(
            "items_is_favorite_idx", "is_favorite",
            postgresql_where=text("is_favorite = true"),
        ),
        Index(
            "items_deleted_at_idx", "deleted_at",
            postgresql_where=text("deleted_at IS NOT NULL"),
        ),
        Index(
            "items_name_type_uniq", "name", "item_type",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class RecipeDetail(Base):
    """Recipe-only fields keyed by item_id. Never queried directly; always through Item."""
    __tablename__ = "recipe_details"

    item_id = Column(
        Integer, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True
    )
    description = Column(Text, nullable=True)
    ingredients = Column(JSONB, nullable=False, server_default="[]")  # list[dict]
    instructions = Column(Text, nullable=True)
    prep_time_minutes = Column(Integer, nullable=True)
    cook_time_minutes = Column(Integer, nullable=True)
    servings = Column(Integer, nullable=True)
    image_url = Column(Text, nullable=True)

    item = relationship("Item", back_populates="recipe_detail", lazy="selectin")


class FoodItemDetail(Base):
    """Food-item-only fields keyed by item_id. Never queried directly; always through Item."""
    __tablename__ = "food_item_details"

    item_id = Column(
        Integer, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True
    )
    category = Column(Text, nullable=False, server_default="Other")
    shopping_quantity = Column(Numeric, nullable=False, server_default="1.0")
    shopping_unit = Column(Text, nullable=False, server_default="each")

    item = relationship("Item", back_populates="food_item_detail", lazy="selectin")


class MealSlotType(Base):
    __tablename__ = "meal_slot_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    color = Column(String, nullable=True)  # Hex color for badge/swimlane
    icon = Column(String, nullable=True)  # Emoji or icon name
    is_default = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    default_participants = Column(JSON, nullable=True)  # Array of family_member_ids; [] = everyone
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)

    meal_entries = relationship("MealEntry", back_populates="meal_slot_type")


class MealEntry(Base):
    """A single meal slot entry — either references an Item (recipe or food_item) via
    item_id, or stands alone as an ad-hoc meal via custom_meal_name.

    DB invariant (enforced by `meal_entries_item_or_custom_check` CHECK constraint):
        item_id IS NOT NULL OR custom_meal_name IS NOT NULL

    The Item FK is `ON DELETE RESTRICT` — raw `DELETE FROM items` will fail loudly
    with an FK violation rather than silently wiping meal history. The supported
    deletion path is the Expansion B soft-delete flow which sets `items.deleted_at`
    and mirrors into `meal_entries.soft_hidden_at`. See Eng Review #3 Issue 3.
    """
    __tablename__ = "meal_entries"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True, nullable=False)
    meal_slot_type_id = Column(
        Integer, ForeignKey("meal_slot_types.id", ondelete="RESTRICT"), nullable=False
    )
    item_id = Column(
        Integer, ForeignKey("items.id", ondelete="RESTRICT"), nullable=True
    )
    custom_meal_name = Column(String, nullable=True)
    servings = Column(Integer, nullable=True)
    was_cooked = Column(Boolean, default=False)
    notes = Column(String, nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    shopping_sync_status = Column(String, nullable=True)  # "synced", "pending", "failed", "skipped"
    synced_to_list_id = Column(
        Integer, ForeignKey("lists.id", ondelete="SET NULL"), nullable=True
    )
    soft_hidden_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)

    meal_slot_type = relationship("MealSlotType", back_populates="meal_entries")
    item = relationship("Item", back_populates="meal_entries", lazy="selectin")
    participants = relationship(
        "FamilyMember",
        secondary="meal_entry_participants",
        backref="meal_entries",
    )

    __table_args__ = (
        CheckConstraint(
            "item_id IS NOT NULL OR custom_meal_name IS NOT NULL",
            name="meal_entries_item_or_custom_check",
        ),
        Index(
            "meal_entries_item_id_idx", "item_id",
        ),
        Index(
            "meal_entries_soft_hidden_at_idx", "soft_hidden_at",
            postgresql_where=text("soft_hidden_at IS NOT NULL"),
        ),
    )


# Junction table for meal entry ↔ family member (per-person meals)
meal_entry_participants = Table(
    "meal_entry_participants",
    Base.metadata,
    Column("meal_entry_id", Integer, ForeignKey("meal_entries.id", ondelete="CASCADE"), primary_key=True),
    Column("family_member_id", Integer, ForeignKey("family_members.id", ondelete="CASCADE"), primary_key=True),
)


class CalendarIntegration(Base):
    __tablename__ = "calendar_integrations"

    id = Column(Integer, primary_key=True, index=True)
    family_member_id = Column(Integer, ForeignKey("family_members.id"), nullable=False)
    provider = Column(String, nullable=False, default="icloud")
    email = Column(String, nullable=False)
    encrypted_password = Column(String, nullable=False)
    status = Column(
        SQLEnum(IntegrationStatus),
        default=IntegrationStatus.ACTIVE,
        nullable=False,
    )
    last_sync_at = Column(DateTime, nullable=True)
    last_error = Column(String, nullable=True)
    sync_range_past_days = Column(Integer, default=30)
    sync_range_future_days = Column(Integer, default=90)
    selected_calendars = Column(JSON, nullable=True)  # Legacy — migrating to Calendar table

    # Reminders sync status (Phase 2)
    reminders_status = Column(SQLEnum(IntegrationStatus), nullable=True)
    reminders_last_error = Column(String, nullable=True)
    reminders_last_sync_at = Column(DateTime, nullable=True)

    family_member = relationship("FamilyMember", back_populates="calendar_integrations")
    calendars = relationship("Calendar", back_populates="integration", cascade="all, delete-orphan")
    calendar_events = relationship("CalendarEvent", back_populates="integration")
    synced_tasks = relationship("Task", back_populates="integration")
    synced_lists = relationship("List", back_populates="integration")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)


class Calendar(Base):
    __tablename__ = "calendars"

    id = Column(Integer, primary_key=True, index=True)
    calendar_integration_id = Column(
        Integer,
        ForeignKey("calendar_integrations.id", ondelete="CASCADE"),
        nullable=False,
    )
    calendar_url = Column(String, nullable=False)
    name = Column(String, nullable=False)
    color = Column(String, nullable=True)
    is_todo = Column(Boolean, default=False)  # True for reminder lists, False for event calendars

    integration = relationship("CalendarIntegration", back_populates="calendars")
    events = relationship("CalendarEvent", back_populates="calendar")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "calendar_integration_id",
            "calendar_url",
            name="uq_calendar_integration_url",
        ),
    )


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    date = Column(Date, index=True, nullable=False)
    start_time = Column(String, nullable=True)  # HH:MM format, null = all-day
    end_time = Column(String, nullable=True)  # HH:MM format, null = all-day
    all_day = Column(Boolean, default=False)
    source = Column(
        SQLEnum(CalendarEventSource),
        default=CalendarEventSource.MANUAL,
        nullable=False,
    )
    external_id = Column(String, nullable=True)
    assigned_to = Column(Integer, ForeignKey("family_members.id"), nullable=True)
    family_member = relationship("FamilyMember")
    timezone = Column(String, nullable=True)  # IANA timezone name, null for all-day events
    # Sync metadata columns
    etag = Column(String, nullable=True)
    last_modified_remote = Column(DateTime, nullable=True)
    sync_status = Column(String, nullable=True)  # SYNCED, PENDING_PUSH, CONFLICT
    calendar_integration_id = Column(
        Integer,
        ForeignKey("calendar_integrations.id", ondelete="SET NULL"),
        nullable=True,
    )
    calendar_id = Column(
        Integer,
        ForeignKey("calendars.id", ondelete="SET NULL"),
        nullable=True,
    )
    integration = relationship("CalendarIntegration", back_populates="calendar_events")
    calendar = relationship("Calendar", back_populates="events")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "external_id",
            "calendar_integration_id",
            name="uq_calendar_event_external_integration",
        ),
    )


class AppSettings(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    timezone = Column(String, nullable=False, default="UTC")
    # Mealboard settings
    week_start_day = Column(String, nullable=False, default="monday")  # "monday" or "sunday"
    measurement_system = Column(String, nullable=False, default="imperial")  # "imperial" or "metric"
    mealboard_shopping_list_id = Column(
        Integer, ForeignKey("lists.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)


class List(Base):
    __tablename__ = "lists"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    color = Column(String, nullable=True)
    icon = Column(String, nullable=True)
    external_id = Column(String, nullable=True)  # CalDAV calendar URL for synced lists
    calendar_integration_id = Column(
        Integer,
        ForeignKey("calendar_integrations.id", ondelete="SET NULL"),
        nullable=True,
    )
    integration = relationship("CalendarIntegration", back_populates="synced_lists")
    tasks = relationship("Task", back_populates="list")
    sections = relationship("Section", back_populates="list", cascade="all, delete-orphan")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)


class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    list_id = Column(Integer, ForeignKey("lists.id", ondelete="CASCADE"), nullable=False)
    sort_order = Column(Integer, default=0)
    external_id = Column(String, nullable=True)
    list = relationship("List", back_populates="sections")
    tasks = relationship("Task", back_populates="section")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)
