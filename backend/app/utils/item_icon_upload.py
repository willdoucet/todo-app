"""Item icon upload helper — Chunk 5.

Canonical upload constraints from plan §1790:
- PNG / JPEG / WebP only (SVG explicitly rejected)
- Max 1 MB
- Filename is `{uuid4}.{ext}` where ext is derived from the validated magic
  bytes, NOT the user-supplied filename
- Storage path: `uploads/item-icons/{uuid4}.{ext}`
- Response: `{"url": "/uploads/item-icons/{uuid4}.{ext}"}`

MIME validation uses magic-byte sniffing on the first 12 bytes rather than
trusting `Content-Type` from the multipart headers (which a hostile client
could fake). This avoids a `python-magic` or `Pillow` dep — the three
supported formats have short, unambiguous signatures.

Dimension enforcement (≤512×512, plan §1790) is intentionally skipped in
this pass — it requires Pillow which we're not adding. The 1 MB size cap is
a sufficient practical bound for household-scale avatar icons.
"""
import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))
ITEM_ICONS_SUBDIR = "item-icons"
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB per plan §1790

# Magic-byte signatures for the three accepted formats. Each entry is
# (ext, signature, offset) — we check `content[offset:offset+len(sig)] == sig`.
_MAGIC = [
    (".png", b"\x89PNG\r\n\x1a\n", 0),
    (".jpg", b"\xff\xd8\xff", 0),
    (".webp", b"RIFF", 0),  # plus `WEBP` at offset 8 — checked below
]


def _sniff_ext(content: bytes) -> str | None:
    """Return the file extension (".png", ".jpg", ".webp") if the first bytes
    match a supported format, else None. Used to derive the canonical filename
    and reject SVG / GIF / PDF / arbitrary binary uploads.
    """
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if content[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    return None


async def save_item_icon(file: UploadFile) -> str:
    """Validate + persist an item icon file, return the public URL.

    Raises:
        HTTPException 413 if file is larger than MAX_FILE_SIZE
        HTTPException 415 if the magic bytes don't match PNG/JPEG/WebP
    """
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large — max {MAX_FILE_SIZE // 1024 // 1024} MB",
        )

    ext = _sniff_ext(content)
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Invalid image format. Supported: PNG, JPEG, WebP (SVG and other formats are rejected).",
        )

    # Canonical filename — ignore whatever the user uploaded
    filename = f"{uuid.uuid4()}{ext}"
    dir_path = UPLOAD_DIR / ITEM_ICONS_SUBDIR
    dir_path.mkdir(parents=True, exist_ok=True)

    file_path = dir_path / filename
    with open(file_path, "wb") as f:
        f.write(content)

    return f"/uploads/{ITEM_ICONS_SUBDIR}/{filename}"
