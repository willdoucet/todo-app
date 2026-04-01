from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from . import models, schemas


async def get_sections(db: AsyncSession, list_id: int):
    stmt = (
        select(models.Section)
        .where(models.Section.list_id == list_id)
        .order_by(models.Section.sort_order, models.Section.id)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_section(db: AsyncSession, section_id: int):
    result = await db.execute(
        select(models.Section).where(models.Section.id == section_id)
    )
    return result.scalar_one_or_none()


async def create_section(db: AsyncSession, list_id: int, section: schemas.SectionCreate):
    # Get max sort_order for this list
    stmt = (
        select(models.Section.sort_order)
        .where(models.Section.list_id == list_id)
        .order_by(models.Section.sort_order.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    max_order = result.scalar_one_or_none() or 0

    db_section = models.Section(
        **section.model_dump(),
        list_id=list_id,
        sort_order=max_order + 1,
    )
    db.add(db_section)
    await db.commit()
    await db.refresh(db_section)
    return db_section


async def update_section(db: AsyncSession, section_id: int, section: schemas.SectionUpdate):
    db_section = await get_section(db, section_id)
    if not db_section:
        return None

    update_data = section.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_section, field, value)

    await db.commit()
    await db.refresh(db_section)
    return db_section


async def delete_section(db: AsyncSession, section_id: int):
    db_section = await get_section(db, section_id)
    if not db_section:
        return False
    await db.delete(db_section)
    await db.commit()
    return True


async def reorder_sections(db: AsyncSession, list_id: int, ordered_ids: list[int]):
    """Reorder sections by setting sort_order based on position in ordered_ids."""
    sections = await get_sections(db, list_id)
    section_map = {s.id: s for s in sections}

    for i, section_id in enumerate(ordered_ids):
        if section_id in section_map:
            section_map[section_id].sort_order = i

    await db.commit()
    return await get_sections(db, list_id)
