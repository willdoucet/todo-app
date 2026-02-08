from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    ARRAY,
    JSON,
    Text,
    func,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship, declarative_base
from enum import Enum as PyEnum

Base = declarative_base()


class ResponsibilityCategory(PyEnum):
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    EVENING = "EVENING"
    CHORE = "CHORE"


class MealCategory(PyEnum):
    BREAKFAST = "BREAKFAST"
    LUNCH = "LUNCH"
    DINNER = "DINNER"


class CalendarEventSource(PyEnum):
    MANUAL = "MANUAL"
    ICLOUD = "ICLOUD"
    GOOGLE = "GOOGLE"


class FamilyMember(Base):
    __tablename__ = "family_members"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    photo_url = Column(String, nullable=True)  # Path to uploaded photo
    color = Column(String, nullable=True)  # Hex color for calendar display

    tasks = relationship("Task", back_populates="family_member")
    responsibilities = relationship("Responsibility", back_populates="family_member")
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
    important = Column(Boolean, default=False)
    list_id = Column(Integer, ForeignKey("lists.id"), nullable=False)
    list = relationship("List", back_populates="tasks")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)


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


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    ingredients = Column(JSON, nullable=True)  # Array of {name, quantity, unit, category}
    instructions = Column(Text, nullable=False)
    prep_time_minutes = Column(Integer, nullable=True)
    cook_time_minutes = Column(Integer, nullable=True)
    servings = Column(Integer, default=4)
    image_url = Column(String, nullable=True)
    is_favorite = Column(Boolean, default=False)
    tags = Column(JSON, nullable=True)  # Array of strings
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)

    meal_plans = relationship("MealPlan", back_populates="recipe")


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True, nullable=False)
    category = Column(SQLEnum(MealCategory), nullable=False)
    recipe_id = Column(
        Integer, ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True
    )
    custom_meal_name = Column(String, nullable=True)
    was_cooked = Column(Boolean, default=False)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)

    recipe = relationship("Recipe", back_populates="meal_plans")


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
    external_id = Column(String, nullable=True, unique=True)
    assigned_to = Column(Integer, ForeignKey("family_members.id"), nullable=True)
    family_member = relationship("FamilyMember")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)


class List(Base):
    __tablename__ = "lists"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    color = Column(String, nullable=True)
    icon = Column(String, nullable=True)
    tasks = relationship("Task", back_populates="list")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)
