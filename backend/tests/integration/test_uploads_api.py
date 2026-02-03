"""
Integration tests for /upload API endpoints.

These tests verify file upload functionality:
- Valid image uploads succeed
- Invalid file types are rejected
- Files too large are rejected
- Stock icons endpoint returns predefined list
"""

import pytest
import io


def create_fake_image(filename: str, content: bytes = b"fake image content") -> tuple:
    """
    Create a fake file for upload testing.

    Returns tuple of (filename, file-like object, content-type) for httpx.
    """
    return (filename, io.BytesIO(content), "image/jpeg")


# =============================================================================
# GET /upload/stock-icons - List stock icons
# =============================================================================

class TestListStockIcons:
    """Tests for GET /upload/stock-icons endpoint."""

    async def test_returns_stock_icons_list(self, client):
        """Should return list of predefined stock icons."""
        response = await client.get("/upload/stock-icons")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 5  # 5 stock icons defined

        # Verify structure of first icon
        first = data[0]
        assert "id" in first
        assert "url" in first
        assert "label" in first

    async def test_stock_icons_have_expected_ids(self, client):
        """Should return icons with expected IDs."""
        response = await client.get("/upload/stock-icons")

        data = response.json()
        ids = [icon["id"] for icon in data]

        assert "brush-teeth" in ids
        assert "make-bed" in ids
        assert "homework" in ids


# =============================================================================
# POST /upload/family-photo - Upload family photo
# =============================================================================

class TestUploadFamilyPhoto:
    """Tests for POST /upload/family-photo endpoint."""

    async def test_uploads_valid_jpg(self, client):
        """Should accept JPG file and return URL."""
        files = {"file": create_fake_image("photo.jpg")}

        response = await client.post("/upload/family-photo", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert data["url"].startswith("/uploads/family_photos/")
        assert data["url"].endswith(".jpg")

    async def test_uploads_valid_png(self, client):
        """Should accept PNG file."""
        files = {"file": ("photo.png", io.BytesIO(b"fake png"), "image/png")}

        response = await client.post("/upload/family-photo", files=files)

        assert response.status_code == 200
        assert response.json()["url"].endswith(".png")

    async def test_uploads_valid_gif(self, client):
        """Should accept GIF file."""
        files = {"file": ("photo.gif", io.BytesIO(b"fake gif"), "image/gif")}

        response = await client.post("/upload/family-photo", files=files)

        assert response.status_code == 200
        assert response.json()["url"].endswith(".gif")

    async def test_uploads_valid_webp(self, client):
        """Should accept WebP file."""
        files = {"file": ("photo.webp", io.BytesIO(b"fake webp"), "image/webp")}

        response = await client.post("/upload/family-photo", files=files)

        assert response.status_code == 200
        assert response.json()["url"].endswith(".webp")

    async def test_rejects_invalid_file_type(self, client):
        """Should reject non-image file types."""
        files = {"file": ("document.pdf", io.BytesIO(b"fake pdf"), "application/pdf")}

        response = await client.post("/upload/family-photo", files=files)

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    async def test_rejects_txt_file(self, client):
        """Should reject text files."""
        files = {"file": ("notes.txt", io.BytesIO(b"some text"), "text/plain")}

        response = await client.post("/upload/family-photo", files=files)

        assert response.status_code == 400

    async def test_rejects_file_too_large(self, client):
        """Should reject files over 5MB."""
        # Create 6MB file
        large_content = b"x" * (6 * 1024 * 1024)
        files = {"file": ("huge.jpg", io.BytesIO(large_content), "image/jpeg")}

        response = await client.post("/upload/family-photo", files=files)

        assert response.status_code == 413
        assert "too large" in response.json()["detail"]

    async def test_generates_unique_filenames(self, client):
        """Each upload should get a unique filename."""
        files1 = {"file": create_fake_image("same.jpg", b"content1")}
        files2 = {"file": create_fake_image("same.jpg", b"content2")}

        response1 = await client.post("/upload/family-photo", files=files1)
        response2 = await client.post("/upload/family-photo", files=files2)

        url1 = response1.json()["url"]
        url2 = response2.json()["url"]

        # Both succeed
        assert response1.status_code == 200
        assert response2.status_code == 200
        # Different URLs (UUID-based)
        assert url1 != url2


# =============================================================================
# POST /upload/responsibility-icon - Upload responsibility icon
# =============================================================================

class TestUploadResponsibilityIcon:
    """Tests for POST /upload/responsibility-icon endpoint."""

    async def test_uploads_valid_image(self, client):
        """Should accept valid image file."""
        files = {"file": create_fake_image("icon.png")}

        response = await client.post("/upload/responsibility-icon", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert data["url"].startswith("/uploads/responsibility_icons/")

    async def test_rejects_invalid_file_type(self, client):
        """Should reject non-image file types."""
        files = {"file": ("script.js", io.BytesIO(b"alert('hi')"), "text/javascript")}

        response = await client.post("/upload/responsibility-icon", files=files)

        assert response.status_code == 400

    async def test_rejects_file_too_large(self, client):
        """Should reject files over 5MB."""
        large_content = b"x" * (6 * 1024 * 1024)
        files = {"file": ("huge.png", io.BytesIO(large_content), "image/png")}

        response = await client.post("/upload/responsibility-icon", files=files)

        assert response.status_code == 413


# =============================================================================
# Edge Cases
# =============================================================================

class TestUploadEdgeCases:
    """Edge case tests for upload endpoints."""

    async def test_uppercase_extension_is_accepted(self, client):
        """Should accept uppercase extensions like .JPG."""
        files = {"file": ("PHOTO.JPG", io.BytesIO(b"content"), "image/jpeg")}

        response = await client.post("/upload/family-photo", files=files)

        assert response.status_code == 200
        # Extension should be lowercased in output
        assert response.json()["url"].endswith(".jpg")

    async def test_accepts_file_exactly_at_size_limit(self, client):
        """Should accept file at exactly 5MB."""
        # Exactly 5MB
        content = b"x" * (5 * 1024 * 1024)
        files = {"file": ("exact.jpg", io.BytesIO(content), "image/jpeg")}

        response = await client.post("/upload/family-photo", files=files)

        assert response.status_code == 200
