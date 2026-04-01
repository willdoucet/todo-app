from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from .. import schemas, crud_sections, crud_lists
from ..database import get_db

router = APIRouter(
    tags=["sections"],
    responses={404: {"description": "Not found"}},
)


@router.get("/lists/{list_id}/sections", response_model=List[schemas.Section])
async def get_sections(list_id: int, db: AsyncSession = Depends(get_db)):
    db_list = await crud_lists.get_list(db, list_id)
    if not db_list:
        raise HTTPException(status_code=404, detail="List not found")
    return await crud_sections.get_sections(db, list_id)


@router.post("/lists/{list_id}/sections", response_model=schemas.Section, status_code=201)
async def create_section(
    list_id: int,
    section: schemas.SectionCreate,
    db: AsyncSession = Depends(get_db),
):
    db_list = await crud_lists.get_list(db, list_id)
    if not db_list:
        raise HTTPException(status_code=404, detail="List not found")
    return await crud_sections.create_section(db, list_id, section)


@router.patch("/sections/{section_id}", response_model=schemas.Section)
async def update_section(
    section_id: int,
    section: schemas.SectionUpdate,
    db: AsyncSession = Depends(get_db),
):
    updated = await crud_sections.update_section(db, section_id, section)
    if not updated:
        raise HTTPException(status_code=404, detail="Section not found")
    return updated


@router.delete("/sections/{section_id}", status_code=204)
async def delete_section(section_id: int, db: AsyncSession = Depends(get_db)):
    success = await crud_sections.delete_section(db, section_id)
    if not success:
        raise HTTPException(status_code=404, detail="Section not found")


@router.post("/lists/{list_id}/sections/reorder", response_model=List[schemas.Section])
async def reorder_sections(
    list_id: int,
    ordered_ids: List[int],
    db: AsyncSession = Depends(get_db),
):
    db_list = await crud_lists.get_list(db, list_id)
    if not db_list:
        raise HTTPException(status_code=404, detail="List not found")
    return await crud_sections.reorder_sections(db, list_id, ordered_ids)
