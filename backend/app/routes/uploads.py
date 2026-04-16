from fastapi import APIRouter, UploadFile, File
from ..uploads import save_upload
from ..utils.item_icon_upload import save_item_icon

router = APIRouter(prefix="/upload", tags=["uploads"])

# Second router at the canonical `/uploads` (plural) prefix for the
# item-icon endpoint per plan §0.3 line 840. Kept as a separate router
# (rather than adding to the legacy singular `/upload` prefix) so the
# public API path matches the plan contract.
item_icon_router = APIRouter(prefix="/uploads", tags=["uploads"])


@item_icon_router.post("/item-icon")
async def upload_item_icon(file: UploadFile = File(...)):
    """Upload a custom icon for an Item (recipe or food_item).

    Validates via magic-byte sniffing (PNG/JPEG/WebP only, SVG rejected),
    enforces a 1 MB cap, writes to `uploads/item-icons/{uuid}.{ext}`, and
    returns the public URL suitable for `Item.icon_url`.

    Plan §1790 canonical upload constraints for Chunk 5.
    """
    url = await save_item_icon(file)
    return {"url": url}


@router.post("/family-photo")
async def upload_family_photo(file: UploadFile = File(...)):
    url = await save_upload(file, "family_photos")
    return {"url": url}


@router.post("/responsibility-icon")
async def upload_responsibility_icon(file: UploadFile = File(...)):
    url = await save_upload(file, "responsibility_icons")
    return {"url": url}


@router.post("/recipe-image")
async def upload_recipe_image(file: UploadFile = File(...)):
    url = await save_upload(file, "recipe_images")
    return {"url": url}


@router.get("/stock-icons")
async def list_stock_icons():
    """Return list of available stock icons."""
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
