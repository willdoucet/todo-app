import os
import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB # File size limit


async def save_upload(file: UploadFile, subdirectory: str) -> str:
    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, detail="Invalid file type. Allowed: {ALLOWED_EXTENSIONS}"
        )

    # Create Filename
    filename = f"{uuid.uuid4()}{ext}"

    # Ensure directory exists
    dir_path = UPLOAD_DIR / subdirectory
    dir_path.mkdir(parents=True, exist_ok=True)

    # Read File and Validate Content
    file_path = dir_path / filename
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large, Max 5MB")

    with open(file_path, "wb") as f:
        f.write(content)

    return f"/uploads/{subdirectory}/{filename}"
