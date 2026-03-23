from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.utils.slugify import generate_slug


async def get_all_categories(db: AsyncSession) -> list[Category]:
    result = await db.execute(select(Category).order_by(Category.id))
    return list(result.scalars().all())


async def get_category_by_id(db: AsyncSession, category_id: int) -> Category:
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


async def create_category(db: AsyncSession, data: CategoryCreate) -> Category:
    slug = generate_slug(data.name_en)
    existing = await db.execute(select(Category).where(Category.slug == slug))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Slug '{slug}' already exists")
    category = Category(name_es=data.name_es, name_en=data.name_en, slug=slug)
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


async def update_category(db: AsyncSession, category_id: int, data: CategoryUpdate) -> Category:
    category = await get_category_by_id(db, category_id)
    if data.name_es is not None:
        category.name_es = data.name_es
    if data.name_en is not None:
        new_slug = generate_slug(data.name_en)
        if new_slug != category.slug:
            existing = await db.execute(select(Category).where(Category.slug == new_slug))
            if existing.scalar_one_or_none() is not None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Slug '{new_slug}' already exists")
            category.slug = new_slug
        category.name_en = data.name_en
    await db.flush()
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, category_id: int) -> None:
    category = await get_category_by_id(db, category_id)
    await db.delete(category)
    await db.flush()
