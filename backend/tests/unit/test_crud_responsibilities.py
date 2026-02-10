"""
Unit tests for crud_responsibilities.py

These tests use mocked database sessions to test business logic
without needing a real database connection.

The key function to test is `toggle_completion`, which has complex
branching logic:
- If responsibility doesn't exist → return (None, False)
- If completion exists → delete it → return (None, False)
- If no completion → create it → return (completion, True)
"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from app.crud_responsibilities import (
    get_responsibility,
    get_responsibilities,
    delete_responsibility,
    toggle_completion,
    get_completions_for_date,
)


# =============================================================================
# get_responsibility tests
# =============================================================================

class TestGetResponsibility:
    """Tests for get_responsibility function."""

    async def test_returns_responsibility_when_found(self, mock_db_session, mock_responsibility):
        """Should return the responsibility when it exists."""
        # Arrange: Configure mock to return our test responsibility
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_responsibility
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await get_responsibility(mock_db_session, responsibility_id=1)

        # Assert
        assert result == mock_responsibility
        assert result.title == "Make bed"
        mock_db_session.execute.assert_called_once()

    async def test_returns_none_when_not_found(self, mock_db_session):
        """Should return None when responsibility doesn't exist."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await get_responsibility(mock_db_session, responsibility_id=999)

        # Assert
        assert result is None


# =============================================================================
# get_responsibilities tests
# =============================================================================

class TestGetResponsibilities:
    """Tests for get_responsibilities function."""

    async def test_returns_all_responsibilities(self, mock_db_session, mock_responsibility):
        """Should return all responsibilities."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_responsibility]
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await get_responsibilities(mock_db_session)

        # Assert
        assert len(result) == 1
        assert result[0].title == "Make bed"

    async def test_returns_empty_list_when_none_exist(self, mock_db_session):
        """Should return empty list when no responsibilities exist."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await get_responsibilities(mock_db_session)

        # Assert
        assert result == []


# =============================================================================
# delete_responsibility tests
# =============================================================================

class TestDeleteResponsibility:
    """Tests for delete_responsibility function."""

    async def test_returns_true_when_deleted(self, mock_db_session, mock_responsibility):
        """Should return True when responsibility is found and deleted."""
        # Arrange: Mock get_responsibility to return the responsibility
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_responsibility
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await delete_responsibility(mock_db_session, responsibility_id=1)

        # Assert
        assert result is True
        mock_db_session.delete.assert_called_once_with(mock_responsibility)
        mock_db_session.commit.assert_called_once()

    async def test_returns_false_when_not_found(self, mock_db_session):
        """Should return False when responsibility doesn't exist."""
        # Arrange: Mock get_responsibility to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await delete_responsibility(mock_db_session, responsibility_id=999)

        # Assert
        assert result is False
        mock_db_session.delete.assert_not_called()
        mock_db_session.commit.assert_not_called()


# =============================================================================
# toggle_completion tests - THE MAIN FOCUS
# =============================================================================

class TestToggleCompletion:
    """
    Tests for toggle_completion function.

    This is the most complex function in the module with three paths:
    1. Responsibility not found → return (None, False)
    2. Completion exists → delete it → return (None, False)
    3. No completion → create it → return (completion, True)
    """

    async def test_returns_none_false_when_responsibility_not_found(self, mock_db_session):
        """
        Path 1: When the responsibility doesn't exist, return (None, False).

        This is an error case - can't toggle completion for non-existent responsibility.
        """
        # Arrange: First query (get_responsibility) returns None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Act
        completion, is_complete = await toggle_completion(
            mock_db_session,
            responsibility_id=999,
            target_date=date.today(),
            family_member_id=1,
            category="MORNING",
        )

        # Assert
        assert completion is None
        assert is_complete is False
        # Should only call execute once (to check responsibility exists)
        assert mock_db_session.execute.call_count == 1
        # Should NOT commit (nothing to do)
        mock_db_session.commit.assert_not_called()

    async def test_deletes_existing_completion_and_returns_none_false(
        self, mock_db_session, mock_responsibility, mock_completion
    ):
        """
        Path 2: When completion already exists, delete it (mark as incomplete).

        This is the "uncomplete" action - user clicking completed task to uncomplete it.
        """
        # Arrange: Two queries:
        # 1. get_responsibility returns the responsibility
        # 2. Check for existing completion returns the completion

        mock_resp_result = MagicMock()
        mock_resp_result.scalar_one_or_none.return_value = mock_responsibility

        mock_completion_result = MagicMock()
        mock_completion_result.scalar_one_or_none.return_value = mock_completion

        # Return different results for each execute call
        mock_db_session.execute.side_effect = [mock_resp_result, mock_completion_result]

        # Act
        completion, is_complete = await toggle_completion(
            mock_db_session,
            responsibility_id=1,
            target_date=date.today(),
            family_member_id=2,
            category="MORNING",
        )

        # Assert
        assert completion is None
        assert is_complete is False
        # Should delete the existing completion
        mock_db_session.delete.assert_called_once_with(mock_completion)
        mock_db_session.commit.assert_called_once()
        # Should NOT add anything
        mock_db_session.add.assert_not_called()

    async def test_creates_completion_and_returns_completion_true(
        self, mock_db_session, mock_responsibility
    ):
        """
        Path 3: When no completion exists, create one (mark as complete).

        This is the "complete" action - user clicking incomplete task to complete it.
        """
        # Arrange: Two queries:
        # 1. get_responsibility returns the responsibility
        # 2. Check for existing completion returns None (no existing completion)

        mock_resp_result = MagicMock()
        mock_resp_result.scalar_one_or_none.return_value = mock_responsibility

        mock_completion_result = MagicMock()
        mock_completion_result.scalar_one_or_none.return_value = None  # No existing completion

        mock_db_session.execute.side_effect = [mock_resp_result, mock_completion_result]

        # Act
        completion, is_complete = await toggle_completion(
            mock_db_session,
            responsibility_id=1,
            target_date=date.today(),
            family_member_id=2,
            category="MORNING",
        )

        # Assert
        assert is_complete is True
        # Should add a new completion
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()
        # Should NOT delete anything
        mock_db_session.delete.assert_not_called()


class TestToggleCompletionEdgeCases:
    """Edge case tests for toggle_completion."""

    async def test_toggle_uses_correct_family_member_id(
        self, mock_db_session, mock_responsibility
    ):
        """
        Completion should be tied to the specific family member.

        This ensures Alice completing a task doesn't affect Bob's completion state.
        """
        # Arrange: Responsibility exists, no completion for this member
        mock_resp_result = MagicMock()
        mock_resp_result.scalar_one_or_none.return_value = mock_responsibility

        mock_completion_result = MagicMock()
        mock_completion_result.scalar_one_or_none.return_value = None

        mock_db_session.execute.side_effect = [mock_resp_result, mock_completion_result]

        target_date = date(2024, 6, 15)
        family_member_id = 42  # Specific member

        # Act
        await toggle_completion(
            mock_db_session,
            responsibility_id=1,
            target_date=target_date,
            family_member_id=family_member_id,
            category="MORNING",
        )

        # Assert: The added completion should have the correct family_member_id
        add_call = mock_db_session.add.call_args
        added_completion = add_call[0][0]
        assert added_completion.family_member_id == family_member_id
        assert added_completion.responsibility_id == 1
        assert added_completion.completion_date == target_date
        assert added_completion.category == "MORNING"

    async def test_toggle_uses_correct_date(
        self, mock_db_session, mock_responsibility
    ):
        """
        Completion should be tied to the specific date.

        Completing Monday's chore shouldn't affect Tuesday's.
        """
        # Arrange
        mock_resp_result = MagicMock()
        mock_resp_result.scalar_one_or_none.return_value = mock_responsibility

        mock_completion_result = MagicMock()
        mock_completion_result.scalar_one_or_none.return_value = None

        mock_db_session.execute.side_effect = [mock_resp_result, mock_completion_result]

        specific_date = date(2024, 12, 25)  # Christmas

        # Act
        await toggle_completion(
            mock_db_session,
            responsibility_id=1,
            target_date=specific_date,
            family_member_id=1,
            category="EVENING",
        )

        # Assert: The added completion should have the correct date and category
        add_call = mock_db_session.add.call_args
        added_completion = add_call[0][0]
        assert added_completion.completion_date == specific_date
        assert added_completion.category == "EVENING"


# =============================================================================
# get_completions_for_date tests
# =============================================================================

class TestGetCompletionsForDate:
    """Tests for get_completions_for_date function."""

    async def test_returns_completions_for_date(self, mock_db_session, mock_completion):
        """Should return all completions for the given date."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_completion]
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await get_completions_for_date(mock_db_session, target_date=date.today())

        # Assert
        assert len(result) == 1
        assert result[0] == mock_completion

    async def test_returns_empty_list_when_no_completions(self, mock_db_session):
        """Should return empty list when no completions exist for the date."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await get_completions_for_date(mock_db_session, target_date=date.today())

        # Assert
        assert result == []
