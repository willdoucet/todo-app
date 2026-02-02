from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from .. import schemas, crud_lists
from ..database import get_db

router = APIRouter(
    prefix="/lists",
    tags=["lists"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[schemas.List])
async def get_lists(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    lists = await crud_lists.get_lists(db, skip=skip, limit=limit)
    return lists


@router.get("/{list_id}", response_model=schemas.List)
async def get_list(list_id: int, db: AsyncSession = Depends(get_db)):
    list_obj = await crud_lists.get_list(db, list_id)
    if list_obj is None:
        raise HTTPException(status_code=404, detail="List not found")
    return list_obj


@router.post("/", response_model=schemas.List, status_code=status.HTTP_201_CREATED)
async def create_list(
    list_to_create: schemas.ListCreate, db: AsyncSession = Depends(get_db)
):
    return await crud_lists.create_list(db, list_to_create)


@router.patch("/{list_id}", response_model=schemas.List)
async def update_list(
    list_id: int, list_update: schemas.ListUpdate, db: AsyncSession = Depends(get_db)
):
    updated_list = await crud_lists.update_list(db, list_id, list_update)
    if updated_list is None:
        raise HTTPException(status_code=404, detail="List not found")
    return updated_list


@router.delete("/{list_id}", response_model=schemas.List)
async def delete_list(list_id: int, db: AsyncSession = Depends(get_db)):
    # Get the list before deleting for the return value
    list_to_delete = await crud_lists.get_list(db, list_id)
    if list_to_delete is None:
        raise HTTPException(status_code=404, detail="List not found")

    await crud_lists.delete_list(db, list_id)
    return list_to_delete
