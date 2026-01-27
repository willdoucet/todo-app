from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from .. import schemas, crud_family_members
from ..database import get_db

router = APIRouter(
    prefix="/family-members",
    tags=["family-members"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[schemas.FamilyMember])
async def get_family_members(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    """Get all family members. Returns 'Everyone' first, then alphabetically."""
    return await crud_family_members.get_family_members(db, skip=skip, limit=limit)


@router.get("/{family_member_id}", response_model=schemas.FamilyMember)
async def get_family_member(family_member_id: int, db: AsyncSession = Depends(get_db)):
    family_member = await crud_family_members.get_family_member(db, family_member_id)
    if family_member is None:
        raise HTTPException(status_code=404, detail="Family member not found")
    return family_member


@router.post(
    "/", response_model=schemas.FamilyMember, status_code=status.HTTP_201_CREATED
)
async def create_family_member(
    family_member: schemas.FamilyMemberCreate, db: AsyncSession = Depends(get_db)
):
    existing = await crud_family_members.get_family_member_by_name(
        db, family_member.name
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Family member with this name already exists",
        )
    return await crud_family_members.create_family_member(db, family_member)


@router.patch("/{family_member_id}", response_model=schemas.FamilyMember)
async def update_family_member(
    family_member_id: int,
    family_member: schemas.FamilyMemberUpdate,
    db: AsyncSession = Depends(get_db),
):
    existing = await crud_family_members.get_family_member(db, family_member_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Family member not found"
        )
    if existing.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update system family member",
        )

    if family_member.name:
        name_exists = await crud_family_members.get_family_member_by_name(
            db, family_member.name
        )
        if name_exists and name_exists.id != family_member_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Family member with this name already exists",
            )
    updated = await crud_family_members.update_family_member(
        db, family_member_id, family_member
    )
    return updated


@router.delete("/{family_member_id}", response_model=schemas.FamilyMember)
async def delete_family_member(
    family_member_id: int, db: AsyncSession = Depends(get_db)
):
    deleted, error = await crud_family_members.delete_family_member(
        db, family_member_id
    )
    if error:
        if error == "Family member not found":
            raise HTTPException(status_code=404, detail=error)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return deleted
