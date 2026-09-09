"""Unit tests for the M7 unified upload validator (Fork 3).

Trusts magic bytes, not filenames/headers. PNG/JPEG/WebP accepted; GIF, SVG,
and faked-extension binaries rejected (415). Per-type caps enforced with a
streaming abort (413).
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.utils.upload_validation import validate_and_read

# Minimal valid magic-byte signatures (payload after the signature is opaque).
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
WEBP = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 32
GIF = b"GIF89a" + b"\x00" * 32
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'

ONE_MB = 1 * 1024 * 1024


def _mock_file(content: bytes, *, size: int | None = None) -> MagicMock:
    """Mock UploadFile: async .read(n) chunked over `content`, `.size` header."""
    f = MagicMock()
    f.size = size
    buffer = {"pos": 0}

    async def _read(n: int = -1) -> bytes:
        start = buffer["pos"]
        chunk = content[start:] if n < 0 else content[start:start + n]
        buffer["pos"] = start + len(chunk)
        return chunk

    f.read = AsyncMock(side_effect=_read)
    return f


class TestAcceptedFormats:
    @pytest.mark.parametrize(
        "content,ext,ctype",
        [
            (PNG, ".png", "image/png"),
            (JPEG, ".jpg", "image/jpeg"),
            (WEBP, ".webp", "image/webp"),
        ],
    )
    async def test_accepts_supported_magic_bytes(self, content, ext, ctype):
        result = await validate_and_read(_mock_file(content), max_bytes=ONE_MB)
        assert result.ext == ext
        assert result.content_type == ctype
        assert result.content == content
        assert result.size_bytes == len(content)


class TestRejectedFormats:
    @pytest.mark.parametrize("content", [GIF, SVG, b"not an image at all", b""])
    async def test_rejects_non_allowlisted_with_415(self, content):
        with pytest.raises(HTTPException) as exc:
            await validate_and_read(_mock_file(content), max_bytes=ONE_MB)
        assert exc.value.status_code == 415

    async def test_gif_rejection_is_the_intended_behavior_change(self):
        """M7 Fork 3: GIF was accepted pre-M7; it must now be rejected."""
        with pytest.raises(HTTPException) as exc:
            await validate_and_read(_mock_file(GIF), max_bytes=ONE_MB)
        assert exc.value.status_code == 415

    async def test_faked_extension_binary_rejected(self):
        """A non-image whose *filename* claims .png is rejected on bytes."""
        f = _mock_file(b"\x7fELF" + b"\x00" * 40)  # an ELF executable
        with pytest.raises(HTTPException) as exc:
            await validate_and_read(f, max_bytes=ONE_MB)
        assert exc.value.status_code == 415


class TestSizeCaps:
    async def test_streaming_abort_over_cap(self):
        oversized = PNG + b"\x00" * (2 * ONE_MB)
        with pytest.raises(HTTPException) as exc:
            await validate_and_read(_mock_file(oversized), max_bytes=ONE_MB)
        assert exc.value.status_code == 413

    async def test_content_length_precheck_rejects_before_read(self):
        # size header alone trips the cap; body never read
        f = _mock_file(PNG, size=2 * ONE_MB)
        with pytest.raises(HTTPException) as exc:
            await validate_and_read(f, max_bytes=ONE_MB)
        assert exc.value.status_code == 413
        f.read.assert_not_called()

    async def test_accepts_exactly_at_cap(self):
        content = PNG + b"\x00" * (ONE_MB - len(PNG))
        assert len(content) == ONE_MB
        result = await validate_and_read(_mock_file(content), max_bytes=ONE_MB)
        assert result.size_bytes == ONE_MB
