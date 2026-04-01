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
        # Arrange: get_list returns None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        update_data = ListUpdate(name="New Name")

        # Act
        result = await update_list(mock_db_session, list_id=999, list=update_data)

        # Assert
        assert result is None

    async def test_updates_and_returns_list_when_found(self, mock_db_session, mock_list):
        """Should update and return the list when found."""
        # Arrange: get_list returns mock_list
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_list
        mock_db_session.execute.return_value = mock_result

        update_data = ListUpdate(name="Updated Name")

        # Act
        result = await update_list(mock_db_session, list_id=1, list=update_data)

        # Assert
        assert result is not None
        mock_db_session.commit.assert_called_once()


# =============================================================================
# delete_list tests
# =============================================================================

class TestDeleteList:
    """Tests for delete_list function."""

    async def test_deletes_local_list(self, mock_db_session, mock_list):
        """Should delete a non-synced list."""
        # Arrange: get_list returns a non-synced list
        mock_list.calendar_integration_id = None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_list
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await delete_list(mock_db_session, list_id=1)

        # Assert
        assert result is True
        mock_db_session.commit.assert_called_once()

    async def test_returns_false_for_nonexistent_list(self, mock_db_session):
        """Should return False when list doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await delete_list(mock_db_session, list_id=999)

        assert result is False

    async def test_blocks_synced_list_deletion(self, mock_db_session, mock_list):
        """Should raise 400 when trying to delete a synced list."""
        from fastapi import HTTPException

        mock_list.calendar_integration_id = 1  # Synced list
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_list
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await delete_list(mock_db_session, list_id=1)

        assert exc_info.value.status_code == 400
        assert "synced" in exc_info.value.detail.lower()
