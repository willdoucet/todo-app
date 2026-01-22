from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    ARRAY,
    Enum as SQLEnum,
    func,
)
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class AssignedTo(str, enum.Enum):
    WILL = "WILL"
    CELINE = "CELINE"
    ALL = "ALL"


class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    due_date = Column(DateTime, nullable=True)
    completed = Column(Boolean, default=False)
    assigned_to = Column(SQLEnum(AssignedTo), default=AssignedTo.ALL, nullable=False)
    important = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)


# class Todo(Base):
#     __tablename__ = "todos"
#     id = Column(Integer, primary_key=True, index=True)
#     title = Column(String, index=True)
#     description = Column(String, nullable=True)
#     due_date = Column(DateTime, nullable=True)
#     completed = Column(Boolean, default=False)


class Recipe(Base):
    __tablename__ = "recipes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    ingredients = Column(ARRAY(String))
    instructions = Column(String)
    prep_time_minutes = Column(Integer, nullable=True)
