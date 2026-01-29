from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import date

from .. import schemas, crud_responsibilities
from ..database import get_db

router = APIRouter(
    prefix="/responsibilities",
    tags=["responsibilities"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[schemas.Responsibility])
async def get_responsibilities(
    skip: int = 0,
    limit: int = 100,
    assigned_to: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all responsibilities, optionally filtered by family member."""
    responsibilities = await crud_responsibilities.get_responsibilities(
        db, skip=skip, limit=limit, assigned_to=assigned_to
    )
    return responsibilities


@router.get("/completions", response_model=List[schemas.ResponsibilityCompletion])
async def get_completions_for_date(
    target_date: date = Query(..., alias="date"),
    db: AsyncSession = Depends(get_db),
):
    """Get all completions for a specific date."""
    completions = await crud_responsibilities.get_completions_for_date(db, target_date)
    return completions


@router.get("/{responsibility_id}", response_model=schemas.Responsibility)
async def get_responsibility(
    responsibility_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single responsibility by ID."""
    responsibility = await crud_responsibilities.get_responsibility(
        db, responsibility_id
    )
    if responsibility is None:
        raise HTTPException(status_code=404, detail="Responsibility not found")
    return responsibility


@router.post(
    "/", response_model=schemas.Responsibility, status_code=status.HTTP_201_CREATED
)
async def create_responsibility(
    responsibility: schemas.ResponsibilityCreate, db: AsyncSession = Depends(get_db)
):
    """Create Responsibility"""
    return await crud_responsibilities.create_responsibility(
        db=db, responsibility=responsibility
    )


@router.patch("/{responsibility_id}", response_model=schemas.Responsibility)
async def update_responsibility(
    responsibility_id: int,
    responsibility_update: schemas.ResponsibilityUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing responsibility."""
    updated = await crud_responsibilities.update_responsibility(
        db, responsibility_id, responsibility_update
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Responsibility not found")
    return updated


@router.delete("/{responsibility_id}", response_model=schemas.Responsibility)
async def delete_responsibility(
    responsibility_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a responsibility and all its completions."""
    deleted = await crud_responsibilities.delete_responsibility(db, responsibility_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Responsibility not found")
    return deleted


@router.post("/{responsibility_id}/complete")
async def toggle_completion(
    responsibility_id: int,
    target_date: date = Query(..., alias="date"),
    family_member_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Toggle completion status for a responsibility on a given date."""
    completion, created = await crud_responsibilities.toggle_completion(
        db, responsibility_id, target_date, family_member_id
    )

    # If both are falsy, check if responsibility exists
    if completion is None and not created:
        resp = await crud_responsibilities.get_responsibility(db, responsibility_id)
        if resp is None:
            raise HTTPException(status_code=404, detail="Responsibility not found")

    return {
        "completed": created,
        "completion": completion,
    }
