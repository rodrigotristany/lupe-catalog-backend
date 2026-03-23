from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from fastapi import HTTPException, status
from app.models.product import Product
from app.models.product_history import ProductHistory
from app.models.category import Category
from app.schemas.product import ProductCreate, ProductUpdate


async def _save_snapshot(db: AsyncSession, product: Product, action: str, username: str = "admin") -> None:
    snapshot = {
        "name_es": product.name_es,
        "name_en": product.name_en,
        "description_es": product.description_es,
        "description_en": product.description_en,
        "price": str(product.price),
        "category_id": product.category_id,
        "is_active": product.is_active,
        "image_paths": [img.image_path for img in product.images],
    }
    history = ProductHistory(
        product_id=product.id,
        action=action,
        snapshot=snapshot,
        changed_by=username,
    )
    db.add(history)


async def _validate_category(db: AsyncSession, category_id: int | None) -> None:
    if category_id is None:
        return
    result = await db.execute(select(Category).where(Category.id == category_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")


async def get_products(
    db: AsyncSession,
    *,
    category_slug: str | None = None,
    search: str | None = None,
    page: int = 1,
    per_page: int = 20,
    sort: str = "created_at",
    order: str = "desc",
    include_inactive: bool = False,
) -> tuple[list[Product], int]:
    per_page = min(per_page, 100)

    query = select(Product)
    if not include_inactive:
        query = query.where(Product.is_active == True)

    if category_slug:
        query = query.join(Category, Product.category_id == Category.id).where(
            Category.slug == category_slug
        )

    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                Product.name_es.ilike(pattern),
                Product.name_en.ilike(pattern),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Sorting
    sort_columns = {
        "created_at": Product.created_at,
        "price": Product.price,
        "name_es": Product.name_es,
        "name_en": Product.name_en,
    }
    sort_col = sort_columns.get(sort, Product.created_at)
    if order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    products = list(result.scalars().all())

    return products, total


async def get_product_by_id(db: AsyncSession, product_id: int, include_inactive: bool = False) -> Product:
    query = select(Product).where(Product.id == product_id)
    if not include_inactive:
        query = query.where(Product.is_active == True)
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


async def create_product(db: AsyncSession, data: ProductCreate, username: str = "admin") -> Product:
    await _validate_category(db, data.category_id)
    product = Product(
        name_es=data.name_es,
        name_en=data.name_en,
        description_es=data.description_es,
        description_en=data.description_en,
        price=data.price,
        category_id=data.category_id,
        is_active=data.is_active,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    await _save_snapshot(db, product, "created", username)
    return product


async def update_product(db: AsyncSession, product_id: int, data: ProductUpdate, username: str = "admin") -> Product:
    product = await get_product_by_id(db, product_id, include_inactive=True)
    if data.name_es is not None:
        product.name_es = data.name_es
    if data.name_en is not None:
        product.name_en = data.name_en
    if data.description_es is not None:
        product.description_es = data.description_es
    if data.description_en is not None:
        product.description_en = data.description_en
    if data.price is not None:
        product.price = data.price
    if data.category_id is not None:
        await _validate_category(db, data.category_id)
        product.category_id = data.category_id
    if data.is_active is not None:
        product.is_active = data.is_active
    await db.flush()
    await db.refresh(product)
    await _save_snapshot(db, product, "updated", username)
    return product


async def soft_delete_product(db: AsyncSession, product_id: int, username: str = "admin") -> None:
    product = await get_product_by_id(db, product_id, include_inactive=True)
    product.is_active = False
    await db.flush()
    await db.refresh(product)
    await _save_snapshot(db, product, "deleted", username)


async def get_product_history(db: AsyncSession, product_id: int) -> list[ProductHistory]:
    # Verify product exists (even if inactive)
    result = await db.execute(select(Product).where(Product.id == product_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    history_result = await db.execute(
        select(ProductHistory)
        .where(ProductHistory.product_id == product_id)
        .order_by(ProductHistory.changed_at.desc())
    )
    return list(history_result.scalars().all())
