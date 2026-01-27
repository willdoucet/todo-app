from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from . import models, schemas


async def get_family_members(db: AsyncSession, skip: int = 0, limit: int = 20):
    stmt = (
        select(models.FamilyMember)
        .offset(skip)
        .limit(limit)
        .order_by(models.FamilyMember.is_system.desc(), models.FamilyMember.name)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_family_member(db: AsyncSession, family_member_id: int):
    stmt = select(models.FamilyMember).where(models.FamilyMember.id == family_member_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_family_member_by_name(db: AsyncSession, name: str):
    stmt = select(models.FamilyMember).where(models.FamilyMember.name == name)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_family_member(
    db: AsyncSession, family_member: schemas.FamilyMemberCreate
):
    db_family_member = models.FamilyMember(**family_member.model_dump())
    db.add(db_family_member)
    await db.commit()
    await db.refresh(db_family_member)
    return db_family_member


async def update_family_member(
    db: AsyncSession, family_member_id: int, family_member: schemas.FamilyMemberUpdate
):
    stmt = (
        update(models.FamilyMember)
        .where(models.FamilyMember.id == family_member_id)
        .values(**family_member.model_dump(exclude_unset=True))
        .returning(models.FamilyMember)
    )
    result = await db.execute(stmt)
    updated_family_member = result.scalar_one_or_none()
    if updated_family_member:
        await db.commit()
        await db.refresh(updated_family_member)
    return updated_family_member


async def delete_family_member(db: AsyncSession, family_member_id: int):
    stmt = select(models.FamilyMember).where(models.FamilyMember.id == family_member_id)
    result = await db.execute(stmt)
    family_member = result.scalar_one_or_none()

    if not family_member:
        return None, "Family member not found"

    if family_member.is_system:
        return None, "Cannot delete system family member"

    task_stmt = select(models.Task).where(models.Task.assigned_to == family_member_id)
    task_result = await db.execute(task_stmt)
    if task_result.scalar_one_or_none():
        return None, "Cannot delete family member with tasks"

    await db.delete(family_member)
    await db.commit()
    return family_member, None
