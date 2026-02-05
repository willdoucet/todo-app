from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from .. import schemas, crud_recipes
from ..database import get_db

router = APIRouter(
    prefix="/recipes",
    tags=["recipes"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[schemas.Recipe])
async def get_recipes(
    skip: int = 0,
    limit: int = 100,
    favorites_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List all recipes, optionally filtered to favorites."""
    recipes = await crud_recipes.get_recipes(
        db, skip=skip, limit=limit, favorites_only=favorites_only
    )
    return recipes


@router.get("/{recipe_id}", response_model=schemas.Recipe)
async def get_recipe(recipe_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single recipe by ID."""
    recipe = await crud_recipes.get_recipe(db, recipe_id=recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.post("/", response_model=schemas.Recipe, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    recipe: schemas.RecipeCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new recipe."""
    return await crud_recipes.create_recipe(db=db, recipe=recipe)


@router.patch("/{recipe_id}", response_model=schemas.Recipe)
async def update_recipe(
    recipe_id: int,
    recipe_update: schemas.RecipeUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing recipe."""
    updated_recipe = await crud_recipes.update_recipe(db, recipe_id, recipe_update)
    if updated_recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return updated_recipe


@router.delete("/{recipe_id}", response_model=schemas.Recipe)
async def delete_recipe(recipe_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a recipe."""
    deleted_recipe = await crud_recipes.delete_recipe(db, recipe_id)
    if deleted_recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return deleted_recipe
