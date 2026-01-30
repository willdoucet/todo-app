from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    ARRAY,
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


class FamilyMember(Base):
    __tablename__ = "family_members"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    photo_url = Column(String, nullable=True)  # Path to uploaded photo

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
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)


class Responsibility(Base):
    __tablename__ = "responsibilities"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    category = Column(SQLEnum(ResponsibilityCategory), nullable=False)
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

    responsibility = relationship("Responsibility", back_populates="completions")
    family_member = relationship("FamilyMember")

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "responsibility_id",
            "completion_date",
            name="uq_responsibility_completion_date",
        ),
    )


class Recipe(Base):
    __tablename__ = "recipes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    ingredients = Column(ARRAY(String))
    instructions = Column(String)
    prep_time_minutes = Column(Integer, nullable=True)
