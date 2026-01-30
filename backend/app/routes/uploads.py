from fastapi import APIRouter, UploadFile, File
from ..uploads import save_upload

router = APIRouter(prefix="/upload", tags=["uploads"])


@router.post("/family-photo")
async def upload_family_photo(file: UploadFile = File(...)):
    url = await save_upload(file, "family_photos")
    return {"url": url}


@router.post("/responsibility-icon")
async def upload_responsibility_icon(file: UploadFile = File(...)):
    url = await save_upload(file, "responsibility_icons")
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
