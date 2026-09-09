from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import date
from . import models, schemas
from .services import asset_lifecycle


async def get_responsibilities(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    assigned_to: int | None = None,
):
    """Get all responsibilities, optionally filtered by family member."""
    stmt = (
        select(models.Responsibility)
        .options(selectinload(models.Responsibility.family_member))
        .offset(skip)
        .limit(limit)
        .order_by(models.Responsibility.title)
    )
    if assigned_to:
        stmt = stmt.where(models.Responsibility.assigned_to == assigned_to)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_responsibility(db: AsyncSession, responsibility_id: int):
    """Get a single responsibility by ID."""
    stmt = (
        select(models.Responsibility)
        .options(selectinload(models.Responsibility.family_member))
        .where(models.Responsibility.id == responsibility_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_responsibility(
    db: AsyncSession, responsibility: schemas.ResponsibilityCreate
):
    """Create a new responsibility."""
    db_responsibility = models.Responsibility(**responsibility.model_dump())
    db.add(db_responsibility)
    # Adopt the icon (referenced=true) atomically with the insert.
    await asset_lifecycle.adopt(db, db_responsibility.icon_url)
    await db.commit()
    return await get_responsibility(db, db_responsibility.id)


async def update_responsibility(
    db: AsyncSession,
    responsibility_id: int,
    responsibility: schemas.ResponsibilityUpdate,
):
    # Capture the previous icon before the update, for asset cleanup.
    old_icon = (
        await db.execute(
            select(models.Responsibility.icon_url).where(
                models.Responsibility.id == responsibility_id
            )
        )
    ).scalar_one_or_none()

    values = responsibility.model_dump(exclude_unset=True)
    stmt = (
        update(models.Responsibility)
        .where(models.Responsibility.id == responsibility_id)
        .values(**values)
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        return None
    # `icon_url` unchanged if it wasn't in the payload → old == new, no cleanup.
    new_icon = values.get("icon_url", old_icon)
    await asset_lifecycle.adopt(db, new_icon)
    await db.commit()
    # Post-commit: reclaim the replaced icon (only if it actually changed).
    await asset_lifecycle.release_if_replaced(db, old_icon, new_icon)
    return await get_responsibility(db, responsibility_id)


async def delete_responsibility(db: AsyncSession, responsibility_id: int):
    """Delete a responsibility and all its completions (via cascade)."""
    # First check if responsibility exists
    responsibility = await get_responsibility(db, responsibility_id)
    if responsibility:
        old_icon = responsibility.icon_url
        await db.delete(responsibility)
        await db.commit()
        # Post-commit: reclaim the icon object + manifest row.
        await asset_lifecycle.release(db, old_icon)
        return True
    return False


async def get_completions_for_date(db: AsyncSession, target_date: date):
    """Get all completions for a specific date."""
    stmt = select(models.ResponsibilityCompletion).where(
        models.ResponsibilityCompletion.completion_date == target_date
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def toggle_completion(
    db: AsyncSession,
    responsibility_id: int,
    target_date: date,
    family_member_id: int,
    category: str,
):

    # First verify the responsibility exists
    responsibility = await get_responsibility(db, responsibility_id)
    if not responsibility:
        return None, False

    # Check if completion already exists for this date + category
    stmt = select(models.ResponsibilityCompletion).where(
        and_(
            models.ResponsibilityCompletion.responsibility_id == responsibility_id,
            models.ResponsibilityCompletion.completion_date == target_date,
            models.ResponsibilityCompletion.family_member_id == family_member_id,
            models.ResponsibilityCompletion.category == category,
        )
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # Already complete -> delete to mark incomplete
        await db.delete(existing)
        await db.commit()
        return None, False
    else:
        # Not complete -> create completion to mark complete
        completion = models.ResponsibilityCompletion(
            responsibility_id=responsibility_id,
            family_member_id=family_member_id,
            completion_date=target_date,
            category=category,
        )
        db.add(completion)
        await db.commit()
        await db.refresh(completion)
        return completion, True
