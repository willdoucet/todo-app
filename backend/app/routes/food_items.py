from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from typing import List, Optional

from .. import schemas, crud_food_items
from ..database import get_db

router = APIRouter(
    prefix="/food-items",
    tags=["food-items"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[schemas.FoodItem])
async def get_food_items(
    search: Optional[str] = Query(None, description="Search by name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: AsyncSession = Depends(get_db),
):
    """Get all food items with optional search and category filter."""
    return await crud_food_items.get_food_items(db, search=search, category=category)


@router.post("/", response_model=schemas.FoodItem, status_code=status.HTTP_201_CREATED)
async def create_food_item(
    food_item: schemas.FoodItemCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new food item."""
    try:
        return await crud_food_items.create_food_item(db, food_item)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A food item named '{food_item.name}' already exists",
        )


@router.patch("/{food_item_id}", response_model=schemas.FoodItem)
async def update_food_item(
    food_item_id: int,
    food_item_update: schemas.FoodItemUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a food item."""
    try:
        updated = await crud_food_items.update_food_item(db, food_item_id, food_item_update)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A food item with that name already exists",
        )
    if updated is None:
        raise HTTPException(status_code=404, detail="Food item not found")
    return updated


@router.delete("/{food_item_id}", response_model=schemas.FoodItem)
async def delete_food_item(
    food_item_id: int, db: AsyncSession = Depends(get_db)
):
    """Delete a food item. Meal entries referencing it keep their data (food_item_id set to NULL)."""
    deleted = await crud_food_items.delete_food_item(db, food_item_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Food item not found")
    return deleted
