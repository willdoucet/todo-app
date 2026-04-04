from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from . import models, schemas


async def get_food_items(
    db: AsyncSession,
    search: str | None = None,
    category: str | None = None,
):
    """Get food items with optional search and category filter."""
    stmt = select(models.FoodItem).order_by(models.FoodItem.name)
    if search:
        stmt = stmt.where(models.FoodItem.name.ilike(f"%{search}%"))
    if category:
        stmt = stmt.where(models.FoodItem.category == category)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_food_item(db: AsyncSession, food_item_id: int):
    """Get a single food item by ID."""
    stmt = select(models.FoodItem).where(models.FoodItem.id == food_item_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_food_item(db: AsyncSession, food_item: schemas.FoodItemCreate):
    """Create a new food item."""
    db_item = models.FoodItem(**food_item.model_dump())
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item


async def update_food_item(
    db: AsyncSession, food_item_id: int, food_item: schemas.FoodItemUpdate
):
    """Update an existing food item."""
    data = food_item.model_dump(exclude_unset=True)
    if not data:
        return await get_food_item(db, food_item_id)
    stmt = (
        update(models.FoodItem)
        .where(models.FoodItem.id == food_item_id)
        .values(**data)
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        return None
    await db.commit()
    return await get_food_item(db, food_item_id)


async def delete_food_item(db: AsyncSession, food_item_id: int):
    """Delete a food item. Meal entries referencing it will have food_item_id set to NULL."""
    item = await get_food_item(db, food_item_id)
    if item:
        await db.delete(item)
        await db.commit()
    return item
