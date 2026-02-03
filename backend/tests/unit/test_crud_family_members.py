"""
Unit tests for crud_family_members.py

These tests use mocked database sessions to test business logic
without needing a real database connection.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.crud_family_members import (
    get_family_member,
    get_family_member_by_name,
    delete_family_member,
)


# =============================================================================
# get_family_member tests
# =============================================================================

class TestGetFamilyMember:
    """Tests for get_family_member function."""

    async def test_returns_member_when_found(self, mock_db_session, mock_family_member):
        """Should return the family member when it exists."""
        # Arrange: Configure mock to return our test member
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_family_member
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await get_family_member(mock_db_session, family_member_id=1)

        # Assert
        assert result == mock_family_member
        assert result.name == "Alice"
        mock_db_session.execute.assert_called_once()

    async def test_returns_none_when_not_found(self, mock_db_session):
        """Should return None when family member doesn't exist."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await get_family_member(mock_db_session, family_member_id=999)

        # Assert
        assert result is None


# =============================================================================
# get_family_member_by_name tests
# =============================================================================

class TestGetFamilyMemberByName:
    """Tests for get_family_member_by_name function."""

    async def test_returns_member_when_found(self, mock_db_session, mock_family_member):
        """Should return the family member when name matches."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_family_member
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await get_family_member_by_name(mock_db_session, name="Alice")

        # Assert
        assert result == mock_family_member
        assert result.name == "Alice"

    async def test_returns_none_when_not_found(self, mock_db_session):
        """Should return None when no member has that name."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await get_family_member_by_name(mock_db_session, name="NonExistent")

        # Assert
        assert result is None


# =============================================================================
# delete_family_member tests
# =============================================================================

class TestDeleteFamilyMember:
    """Tests for delete_family_member function.

    This function has complex validation logic:
    1. Check if member exists
    2. Check if member is a system member
    3. Check if member has assigned tasks
    4. Only then delete
    """

    async def test_returns_error_when_member_not_found(self, mock_db_session):
        """Should return error tuple when family member doesn't exist."""
        # Arrange: First query (find member) returns None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Act
        member, error = await delete_family_member(mock_db_session, family_member_id=999)

        # Assert
        assert member is None
        assert error == "Family member not found"
        mock_db_session.delete.assert_not_called()
        mock_db_session.commit.assert_not_called()

    async def test_returns_error_when_deleting_system_member(self, mock_db_session, mock_system_member):
        """Should not allow deletion of system members (like 'Everyone')."""
        # Arrange: First query returns system member
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_system_member
        mock_db_session.execute.return_value = mock_result

        # Act
        member, error = await delete_family_member(mock_db_session, family_member_id=1)

        # Assert
        assert member is None
        assert error == "Cannot delete system family member"
        mock_db_session.delete.assert_not_called()
        mock_db_session.commit.assert_not_called()

    async def test_returns_error_when_member_has_tasks(self, mock_db_session, mock_family_member, mock_task):
        """Should not allow deletion of members who have assigned tasks."""
        # Arrange: Need to handle two queries:
        # 1. Find the member (returns mock_family_member)
        # 2. Check for tasks (returns mock_task)

        mock_member_result = MagicMock()
        mock_member_result.scalar_one_or_none.return_value = mock_family_member

        mock_task_result = MagicMock()
        mock_task_result.scalar_one_or_none.return_value = mock_task  # Has a task!

        # Return different results for each execute call
        mock_db_session.execute.side_effect = [mock_member_result, mock_task_result]

        # Act
        member, error = await delete_family_member(mock_db_session, family_member_id=1)

        # Assert
        assert member is None
        assert error == "Cannot delete family member with tasks"
        mock_db_session.delete.assert_not_called()
        mock_db_session.commit.assert_not_called()

    async def test_successfully_deletes_member_without_tasks(self, mock_db_session, mock_family_member):
        """Should delete member when all validations pass."""
        # Arrange: Two queries:
        # 1. Find member (returns mock_family_member)
        # 2. Check for tasks (returns None - no tasks)

        mock_member_result = MagicMock()
        mock_member_result.scalar_one_or_none.return_value = mock_family_member

        mock_task_result = MagicMock()
        mock_task_result.scalar_one_or_none.return_value = None  # No tasks

        mock_db_session.execute.side_effect = [mock_member_result, mock_task_result]

        # Act
        member, error = await delete_family_member(mock_db_session, family_member_id=1)

        # Assert
        assert member == mock_family_member
        assert error is None
        mock_db_session.delete.assert_called_once_with(mock_family_member)
        mock_db_session.commit.assert_called_once()


# =============================================================================
# Edge cases
# =============================================================================

class TestDeleteFamilyMemberEdgeCases:
    """Edge case tests for delete_family_member."""

    async def test_system_check_happens_before_task_check(self, mock_db_session):
        """System member check should happen before checking for tasks.

        This ensures we don't waste a database query checking tasks
        for a system member that can never be deleted anyway.
        """
        # Arrange: System member that also has tasks
        mock_system_with_tasks = MagicMock()
        mock_system_with_tasks.id = 1
        mock_system_with_tasks.name = "Everyone"
        mock_system_with_tasks.is_system = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_system_with_tasks
        mock_db_session.execute.return_value = mock_result

        # Act
        member, error = await delete_family_member(mock_db_session, family_member_id=1)

        # Assert: Should fail on system check, not task check
        assert error == "Cannot delete system family member"
        # Should only have one execute call (finding member), not two (no task check)
        assert mock_db_session.execute.call_count == 1
