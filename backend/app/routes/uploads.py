from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..uploads import ICON_MAX_BYTES, PHOTO_MAX_BYTES, store_upload

router = APIRouter(prefix="/upload", tags=["uploads"])

# Second router at the canonical `/uploads` (plural) prefix for the
# item-icon endpoint. Kept as a separate router (rather than adding to the
# legacy singular `/upload` prefix) so the public API path matches the plan
# contract. Registered BEFORE the /uploads read surface in main.py so the
# POST wins over the catch-all (M7 PR2 will add a GET /uploads/{key} proxy).
item_icon_router = APIRouter(prefix="/uploads", tags=["uploads"])


@item_icon_router.post("/item-icon")
async def upload_item_icon(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a custom icon for an Item (recipe or food_item).

    Magic-byte validation (PNG/JPEG/WebP only, GIF/SVG rejected), 1 MB cap,
    stored at `item-icons/{uuid}.{ext}` with an `assets` manifest row.
    """
    url = await store_upload(db, file, "item-icons", max_bytes=ICON_MAX_BYTES)
    return {"url": url}


@router.post("/family-photo")
async def upload_family_photo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    url = await store_upload(db, file, "family_photos", max_bytes=PHOTO_MAX_BYTES)
    return {"url": url}


@router.post("/responsibility-icon")
async def upload_responsibility_icon(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    url = await store_upload(
        db, file, "responsibility_icons", max_bytes=ICON_MAX_BYTES
    )
    return {"url": url}


@router.post("/recipe-image")
async def upload_recipe_image(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    url = await store_upload(db, file, "recipe_images", max_bytes=PHOTO_MAX_BYTES)
    return {"url": url}


@router.get("/stock-icons")
async def list_stock_icons():
    """Return list of available stock icons.

    Stock icons stay bundled + unmanaged (no `assets` row) and keep the
    existing `/uploads/stock_icons/*.png` URL scheme so already-adopted
    references keep resolving (M7 PR2 serves them via the read-proxy's
    stock_icons compat branch).
    """
    return [
        {
            "id": "brush-teeth",
            "url": "/uploads/stock_icons/brush-teeth.png",
            "label": "Brush Teeth",
        },
        {
            "id": "get-dressed",
            "url": "/uploads/stock_icons/get-dressed.png",
            "label": "Get Dressed",
        },
        {
            "id": "take-bath",
            "url": "/uploads/stock_icons/take-bath.png",
            "label": "Take a Bath",
        },
        {
            "id": "make-bed",
            "url": "/uploads/stock_icons/make-bed.png",
            "label": "Make Bed",
        },
        {
            "id": "homework",
            "url": "/uploads/stock_icons/homework.png",
            "label": "Homework",
        },
    ]
