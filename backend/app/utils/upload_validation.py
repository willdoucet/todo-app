"""Unified upload validation (M7 Fork 3).

One validator for ALL upload types, replacing the pre-M7 split between the
filename-extension-trusting ``uploads.save_upload`` (deleted) and the
magic-byte ``item_icon_upload.save_item_icon`` (folded in here).

Trusts BYTES, not headers or filenames:
  - allowlist PNG / JPEG / WebP by magic-byte signature
  - GIF and SVG (and everything else) are rejected  ← the one M7 behavior change
  - per-type size cap passed by the caller (icons 1 MB, photos/recipe 5 MB)
  - streaming abort: an oversized body is rejected without buffering it whole

The derived extension comes from the validated magic bytes, never from the
user-supplied filename.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, UploadFile, status

_CHUNK = 64 * 1024

# ext -> canonical content-type, resolved from the magic-byte match in _sniff_ext.
_CONTENT_TYPE = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".webp": "image/webp",
}


def _sniff_ext(content: bytes) -> str | None:
    """Return ``.png`` / ``.jpg`` / ``.webp`` if the leading bytes match a
    supported signature, else ``None`` (rejects GIF / SVG / PDF / faked-
    extension binaries — none carry these signatures)."""
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if content[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    return None


@dataclass(frozen=True)
class ValidatedUpload:
    content: bytes
    ext: str
    content_type: str
    size_bytes: int


async def validate_and_read(file: UploadFile, *, max_bytes: int) -> ValidatedUpload:
    """Read + validate an uploaded file. Raises ``HTTPException`` 413 (too
    large) or 415 (not an allowed image). On success returns the bytes plus
    the magic-derived extension and content-type."""
    max_mb = max_bytes // 1024 // 1024

    # Cheap pre-check on the Content-Length header (set by Starlette when
    # present) — rejects an obviously-oversized upload without reading the body.
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File too large — max {max_mb} MB",
        )

    # Stream-read; abort the moment the running total exceeds the cap. Defends
    # against clients that lie about Content-Length or use chunked encoding.
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File too large — max {max_mb} MB",
            )
        chunks.append(chunk)
    content = b"".join(chunks)

    ext = _sniff_ext(content)
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Invalid image format. Supported: PNG, JPEG, WebP "
                "(GIF, SVG, and other formats are rejected)."
            ),
        )

    return ValidatedUpload(
        content=content,
        ext=ext,
        content_type=_CONTENT_TYPE[ext],
        size_bytes=total,
    )
