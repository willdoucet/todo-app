"""
Unit tests for uploads.py

These tests verify file upload validation:
- Extension validation (only images allowed)
- File size validation (max 5MB)
- Correct URL path generation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from pathlib import Path

from app.uploads import save_upload, ALLOWED_EXTENSIONS, MAX_FILE_SIZE


# =============================================================================
# Helper to create mock UploadFile
# =============================================================================

def create_mock_upload_file(filename: str, content: bytes) -> MagicMock:
    """
    Create a mock FastAPI UploadFile object.

    UploadFile has:
    - filename: str
    - read(): async method that returns bytes
    """
    mock_file = MagicMock()
    mock_file.filename = filename
    # read() is async, so we use AsyncMock
    mock_file.read = AsyncMock(return_value=content)
    return mock_file


# =============================================================================
# Extension Validation Tests
# =============================================================================

class TestExtensionValidation:
    """Tests for file extension validation."""

    @pytest.mark.parametrize("ext", [".jpg", ".jpeg", ".png", ".gif", ".webp"])
    async def test_accepts_valid_image_extensions(self, ext, tmp_path):
        """Should accept all allowed image extensions."""
        # Arrange
        filename = f"test_image{ext}"
        content = b"fake image content"
        mock_file = create_mock_upload_file(filename, content)

        # Patch UPLOAD_DIR to use temp directory
        with patch("app.uploads.UPLOAD_DIR", tmp_path):
            # Act
            result = await save_upload(mock_file, "photos")

        # Assert: Should return a URL path
        assert result.startswith("/uploads/photos/")
        assert result.endswith(ext)

    @pytest.mark.parametrize("ext", [".txt", ".pdf", ".exe", ".js", ".html", ".svg"])
    async def test_rejects_invalid_extensions(self, ext):
        """Should reject non-image file extensions."""
        # Arrange
        filename = f"malicious{ext}"
        content = b"not an image"
        mock_file = create_mock_upload_file(filename, content)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await save_upload(mock_file, "photos")

        assert exc_info.value.status_code == 400
        assert "Invalid file type" in exc_info.value.detail

    async def test_extension_check_is_case_insensitive(self, tmp_path):
        """Should accept uppercase extensions like .JPG, .PNG."""
        # Arrange
        mock_file = create_mock_upload_file("IMAGE.JPG", b"content")

        with patch("app.uploads.UPLOAD_DIR", tmp_path):
            # Act
            result = await save_upload(mock_file, "photos")

        # Assert: Should succeed (extension lowercased internally)
        assert result.endswith(".jpg")


# =============================================================================
# File Size Validation Tests
# =============================================================================

class TestFileSizeValidation:
    """Tests for file size validation (max 5MB)."""

    async def test_accepts_file_under_5mb(self, tmp_path):
        """Should accept files smaller than 5MB."""
        # Arrange: 1MB file
        content = b"x" * (1 * 1024 * 1024)
        mock_file = create_mock_upload_file("small.jpg", content)

        with patch("app.uploads.UPLOAD_DIR", tmp_path):
            # Act
            result = await save_upload(mock_file, "photos")

        # Assert
        assert result.startswith("/uploads/photos/")

    async def test_accepts_file_exactly_5mb(self, tmp_path):
        """Should accept files exactly at 5MB limit."""
        # Arrange: Exactly 5MB
        content = b"x" * MAX_FILE_SIZE
        mock_file = create_mock_upload_file("exact.png", content)

        with patch("app.uploads.UPLOAD_DIR", tmp_path):
            # Act
            result = await save_upload(mock_file, "photos")

        # Assert
        assert result.startswith("/uploads/photos/")

    async def test_rejects_file_over_5mb(self, tmp_path):
        """Should reject files larger than 5MB."""
        # Arrange: 6MB file (over limit)
        content = b"x" * (6 * 1024 * 1024)
        mock_file = create_mock_upload_file("huge.jpg", content)

        # Note: We still need to patch UPLOAD_DIR because the code
        # creates the directory BEFORE checking file size
        with patch("app.uploads.UPLOAD_DIR", tmp_path):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await save_upload(mock_file, "photos")

        assert exc_info.value.status_code == 413
        assert "File too large" in exc_info.value.detail


# =============================================================================
# URL Path Generation Tests
# =============================================================================

class TestUrlPathGeneration:
    """Tests for the returned URL path format."""

    async def test_returns_correct_url_format(self, tmp_path):
        """Should return URL in format /uploads/{subdirectory}/{uuid}.{ext}."""
        # Arrange
        mock_file = create_mock_upload_file("photo.jpg", b"content")

        with patch("app.uploads.UPLOAD_DIR", tmp_path):
            # Act
            result = await save_upload(mock_file, "family-photos")

        # Assert
        assert result.startswith("/uploads/family-photos/")
        assert result.endswith(".jpg")
        # UUID is 36 chars, so filename is 36 + 4 (.jpg) = 40 chars
        filename = result.split("/")[-1]
        assert len(filename) == 40  # uuid (36) + .jpg (4)

    async def test_generates_unique_filenames(self, tmp_path):
        """Each upload should get a unique UUID filename."""
        # Arrange
        mock_file1 = create_mock_upload_file("same_name.png", b"content1")
        mock_file2 = create_mock_upload_file("same_name.png", b"content2")

        with patch("app.uploads.UPLOAD_DIR", tmp_path):
            # Act
            result1 = await save_upload(mock_file1, "photos")
            result2 = await save_upload(mock_file2, "photos")

        # Assert: Different UUIDs even for same original filename
        assert result1 != result2


# =============================================================================
# File Writing Tests
# =============================================================================

class TestFileWriting:
    """Tests for actual file creation."""

    async def test_creates_subdirectory_if_not_exists(self, tmp_path):
        """Should create the subdirectory if it doesn't exist."""
        # Arrange
        mock_file = create_mock_upload_file("test.jpg", b"content")
        subdir = "new-directory"

        with patch("app.uploads.UPLOAD_DIR", tmp_path):
            # Act
            await save_upload(mock_file, subdir)

        # Assert: Directory was created
        assert (tmp_path / subdir).exists()
        assert (tmp_path / subdir).is_dir()

    async def test_writes_file_content_correctly(self, tmp_path):
        """Should write the exact file content to disk."""
        # Arrange
        original_content = b"This is the actual file content!"
        mock_file = create_mock_upload_file("test.png", original_content)

        with patch("app.uploads.UPLOAD_DIR", tmp_path):
            # Act
            url = await save_upload(mock_file, "photos")

        # Assert: File was written with correct content
        filename = url.split("/")[-1]
        written_path = tmp_path / "photos" / filename
        assert written_path.exists()
        assert written_path.read_bytes() == original_content
