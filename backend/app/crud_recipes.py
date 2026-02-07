from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from . import models, schemas


async def get_recipes(
    db: AsyncSession, skip: int = 0, limit: int = 100, favorites_only: bool = False
):
    """Get all recipes, optionally filtered by favorites."""
    stmt = select(models.Recipe)
    if favorites_only:
        stmt = stmt.where(models.Recipe.is_favorite == True)
    stmt = stmt.offset(skip).limit(limit).order_by(models.Recipe.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_recipe(db: AsyncSession, recipe_id: int):
    """Get a single recipe by ID."""
    stmt = select(models.Recipe).where(models.Recipe.id == recipe_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_recipe(db: AsyncSession, recipe: schemas.RecipeCreate):
    """Create a new recipe."""
    recipe_data = recipe.model_dump()
    # Convert Ingredient objects to dicts for JSON storage
    if recipe_data.get("ingredients"):
        recipe_data["ingredients"] = [
            ing if isinstance(ing, dict) else ing.model_dump()
            for ing in recipe_data["ingredients"]
        ]
    db_recipe = models.Recipe(**recipe_data)
    db.add(db_recipe)
    await db.commit()
    await db.refresh(db_recipe)
    return db_recipe


async def update_recipe(db: AsyncSession, recipe_id: int, recipe: schemas.RecipeUpdate):
    """Update an existing recipe."""
    update_data = recipe.model_dump(exclude_unset=True)
    # Convert Ingredient objects to dicts for JSON storage
    if update_data.get("ingredients"):
        update_data["ingredients"] = [
            ing if isinstance(ing, dict) else ing.model_dump()
            for ing in update_data["ingredients"]
        ]
    stmt = (
        update(models.Recipe)
        .where(models.Recipe.id == recipe_id)
        .values(**update_data)
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        return None
    await db.commit()
    return await get_recipe(db, recipe_id)


async def delete_recipe(db: AsyncSession, recipe_id: int):
    """Delete a recipe."""
    recipe = await get_recipe(db, recipe_id)
    if recipe:
        await db.delete(recipe)
        await db.commit()
    return recipe
