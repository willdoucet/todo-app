"""Integration tests for POST /uploads/item-icon (Chunk 5).

Covers the magic-byte validation (PNG/JPEG/WebP only, SVG rejected) and the
1 MB size cap from plan §1790.
"""
import io

import pytest


# Minimal 1x1 PNG. Only the first 8 bytes need to be a valid PNG signature
# for our magic-byte sniffer to accept it; the rest of the file contents are
# passed through unchanged and stored on disk.
MINIMAL_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50  # ~58 bytes, valid signature

# Fake SVG content — the magic bytes will NOT match PNG/JPEG/WebP
SVG_CONTENT = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>'


class TestItemIconUpload:
    async def test_png_upload_succeeds(self, client):
        response = await client.post(
            "/uploads/item-icon",
            files={"file": ("tiny.png", io.BytesIO(MINIMAL_PNG), "image/png")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert data["url"].startswith("/uploads/item-icons/")
        # Canonical filename is a UUID — the caller-provided "tiny.png" is NOT
        # trusted; the extension is derived from the validated magic bytes.
        assert data["url"].endswith(".png")
        assert "tiny" not in data["url"]

    async def test_svg_rejected_with_415(self, client):
        """SVG must fail the magic-byte sniff even though the content-type
        header would suggest it's an image. The validator trusts bytes, not
        headers."""
        response = await client.post(
            "/uploads/item-icon",
            files={"file": ("fake.svg", io.BytesIO(SVG_CONTENT), "image/svg+xml")},
        )
        assert response.status_code == 415
        assert "SVG" in response.json()["detail"]

    async def test_empty_file_rejected_with_415(self, client):
        """An empty buffer has no magic bytes → 415 Unsupported Media Type."""
        response = await client.post(
            "/uploads/item-icon",
            files={"file": ("empty.png", io.BytesIO(b""), "image/png")},
        )
        assert response.status_code == 415

    async def test_oversize_file_rejected_with_413(self, client):
        """2 MB of arbitrary bytes → 413 Payload Too Large before magic-byte
        validation even runs."""
        big = b"\x00" * (2 * 1024 * 1024)
        response = await client.post(
            "/uploads/item-icon",
            files={"file": ("big.png", io.BytesIO(big), "image/png")},
        )
        assert response.status_code == 413

    async def test_missing_file_rejected_with_422(self, client):
        """FastAPI multipart validation fires before our handler runs."""
        response = await client.post("/uploads/item-icon")
        assert response.status_code == 422
