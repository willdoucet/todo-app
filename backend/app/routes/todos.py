from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from .. import schemas, crud
from ..database import get_db

router = APIRouter(
    prefix="/todos",
    tags=["todos"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[schemas.Todo])
async def get_todos(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    todos = await crud.get_todos(db, skip=skip, limit=limit)
    return todos


@router.get("/{todo_id}", response_model=schemas.Todo)
async def read_todo(todo_id: int, db: AsyncSession = Depends(get_db)):
    todo = await crud.get_todo(db, todo_id=todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.post("/", response_model=schemas.Todo, status_code=status.HTTP_201_CREATED)
async def create_todo(todo: schemas.TodoCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_todo(db=db, todo=todo)


@router.patch("/{todo_id}", response_model=schemas.Todo)
async def update_todo(
    todo_id: int, todo_update: schemas.TodoUpdate, db: AsyncSession = Depends(get_db)
):
    updated_todo = await crud.update_todo(db, todo_id, todo_update)
    if updated_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return updated_todo


@router.delete("/{todo_id}", response_model=schemas.Todo)
async def delete_todo(todo_id: int, db: AsyncSession = Depends(get_db)):
    deleted_todo = await crud.delete_todo(db, todo_id)
    if deleted_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return deleted_todo
