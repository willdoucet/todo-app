"""
Unit tests for crud_lists.py

These tests use mocked database sessions to test business logic
without needing a real database connection.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.crud_lists import (
    get_list,
    get_lists,
    update_list,
    delete_list,
)
from app.schemas import ListUpdate


# =============================================================================
# get_list tests
# =============================================================================

class TestGetList:
    """Tests for get_list function."""

    async def test_returns_list_when_found(self, mock_db_session, mock_list):
        """Should return the list when it exists."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_list
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await get_list(mock_db_session, list_id=1)

        # Assert
        assert result == mock_list
        assert result.name == "Personal"
        mock_db_session.execute.assert_called_once()

    async def test_returns_none_when_not_found(self, mock_db_session):
        """Should return None when list doesn't exist."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await get_list(mock_db_session, list_id=999)

        # Assert
        assert result is None


# =============================================================================
# get_lists tests
# =============================================================================

class TestGetLists:
    """Tests for get_lists function."""

    async def test_returns_all_lists(self, mock_db_session, mock_list):
        """Should return all lists."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_list]
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await get_lists(mock_db_session)

        # Assert
        assert len(result) == 1
        assert result[0].name == "Personal"

    async def test_returns_empty_list_when_none_exist(self, mock_db_session):
        """Should return empty list when no lists exist."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await get_lists(mock_db_session)

        # Assert
        assert result == []

    async def test_respects_pagination(self, mock_db_session, mock_list):
        """Should pass skip and limit to query."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_list]
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await get_lists(mock_db_session, skip=5, limit=20)

        # Assert: Verify execute was called (pagination is in the query)
        mock_db_session.execute.assert_called_once()
        assert len(result) == 1


# =============================================================================
# update_list tests
# =============================================================================

class TestUpdateList:
    """Tests for update_list function."""

    async def test_returns_none_when_list_not_found(self, mock_db_session):
        """Should return None when list doesn't exist."""
        # Arrange: Update returns rowcount=0 (no rows updated)
        mock_update_result = MagicMock()
        mock_update_result.rowcount = 0
        mock_db_session.execute.return_value = mock_update_result

        update_data = ListUpdate(name="New Name")

        # Act
        result = await update_list(mock_db_session, list_id=999, list=update_data)

        # Assert
        assert result is None
        mock_db_session.commit.assert_not_called()

    async def test_updates_and_returns_list_when_found(self, mock_db_session, mock_list):
        """Should update and return the list when found."""
        # Arrange: Two calls:
        # 1. Update returns rowcount=1
        # 2. get_list returns the updated list

        mock_update_result = MagicMock()
        mock_update_result.rowcount = 1

        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = mock_list

        mock_db_session.execute.side_effect = [mock_update_result, mock_get_result]

        update_data = ListUpdate(name="Updated Name")

        # Act
        result = await update_list(mock_db_session, list_id=1, list=update_data)

        # Assert
        assert result == mock_list
        mock_db_session.commit.assert_called_once()


# =============================================================================
# delete_list tests
# =============================================================================

class TestDeleteList:
    """Tests for delete_list function.

    Note: This function doesn't check if the list exists before deleting.
    It just executes the delete and commits.
    """

    async def test_executes_delete_and_commits(self, mock_db_session):
        """Should execute delete statement and commit."""
        # Act
        await delete_list(mock_db_session, list_id=1)

        # Assert
        mock_db_session.execute.assert_called_once()
        mock_db_session.commit.assert_called_once()

    async def test_delete_nonexistent_list_still_commits(self, mock_db_session):
        """Deleting non-existent list still executes (no error, just 0 rows affected)."""
        # Act
        await delete_list(mock_db_session, list_id=999)

        # Assert: Still commits (delete is idempotent)
        mock_db_session.commit.assert_called_once()
