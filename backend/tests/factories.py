"""
Test data factories using factory-boy.

Factories provide a clean way to create test objects with sensible defaults.
You can override any field when creating instances:

    # Create with defaults
    member = FamilyMemberFactory()

    # Override specific fields
    member = FamilyMemberFactory(name="Custom Name", is_system=True)

    # Build without saving (returns dict-like object)
    member_data = FamilyMemberFactory.build()
"""

import factory
from datetime import date, timedelta
from app.models import FamilyMember, Task, List, Responsibility, ResponsibilityCompletion


class FamilyMemberFactory(factory.Factory):
    """Factory for creating FamilyMember instances."""

    class Meta:
        model = FamilyMember

    name = factory.Sequence(lambda n: f"User {n}")
    is_system = False
    photo_url = None


class ListFactory(factory.Factory):
    """Factory for creating List instances."""

    class Meta:
        model = List

    name = factory.Sequence(lambda n: f"List {n}")
    color = "#EF4444"
    icon = "clipboard"


class TaskFactory(factory.Factory):
    """Factory for creating Task instances."""

    class Meta:
        model = Task

    title = factory.Sequence(lambda n: f"Task {n}")
    description = "A task description"
    due_date = factory.LazyFunction(lambda: date.today() + timedelta(days=7))
    completed = False
    important = False
    assigned_to = None
    list_id = None


class ResponsibilityFactory(factory.Factory):
    """Factory for creating Responsibility instances."""

    class Meta:
        model = Responsibility

    title = factory.Sequence(lambda n: f"Responsibility {n}")
    description = "A responsibility description"
    category = "MORNING"
    assigned_to = None
    frequency = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    icon_url = None


class ResponsibilityCompletionFactory(factory.Factory):
    """Factory for creating ResponsibilityCompletion instances."""

    class Meta:
        model = ResponsibilityCompletion

    responsibility_id = None
    family_member_id = None
    completion_date = factory.LazyFunction(date.today)
