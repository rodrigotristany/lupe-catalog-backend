from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, exists
from fastapi import HTTPException, status
from app.models.sale import Sale, SaleProduct
from app.models.product import Product
from app.models.store_settings import StoreSettings
from app.schemas.sale import SaleCreate


async def create_sale(db: AsyncSession, data: SaleCreate) -> Sale:
    settings_result = await db.execute(select(StoreSettings).where(StoreSettings.id == 1))
    store_settings = settings_result.scalar_one_or_none()
    if store_settings is None or data.payment_method not in store_settings.payment_methods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payment method: '{data.payment_method}'",
        )

    product_ids = [item.product_id for item in data.items]
    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate product_id entries in items",
        )

    sale_items: list[SaleProduct] = []
    for item in data.items:
        product_result = await db.execute(select(Product).where(Product.id == item.product_id))
        product = product_result.scalar_one_or_none()
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {item.product_id} not found",
            )
        subtotal = product.price * item.quantity
        cat = product.category
        sale_items.append(
            SaleProduct(
                product_id=product.id,
                product_name_es=product.name_es,
                product_name_en=product.name_en,
                category_id=cat.id if cat else None,
                category_name_es=cat.name_es if cat else None,
                category_name_en=cat.name_en if cat else None,
                price=product.price,
                quantity=item.quantity,
                subtotal=subtotal,
            )
        )

    total = sum(sp.subtotal for sp in sale_items)
    sale = Sale(payment_method=data.payment_method, total=total, items=sale_items)
    db.add(sale)
    await db.flush()
    await db.refresh(sale)
    return sale


async def get_sales(
    db: AsyncSession,
    *,
    product_id: int | None = None,
    category_id: int | None = None,
    payment_method: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    total_min: Decimal | None = None,
    total_max: Decimal | None = None,
    order: str = "desc",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Sale], int]:
    per_page = min(per_page, 100)
    query = select(Sale)

    if product_id is not None:
        query = query.where(
            exists(
                select(SaleProduct.id)
                .where(SaleProduct.sale_id == Sale.id)
                .where(SaleProduct.product_id == product_id)
            )
        )

    if category_id is not None:
        query = query.where(
            exists(
                select(SaleProduct.id)
                .where(SaleProduct.sale_id == Sale.id)
                .where(SaleProduct.category_id == category_id)
            )
        )

    if payment_method is not None:
        query = query.where(Sale.payment_method == payment_method)

    if date_from is not None:
        query = query.where(Sale.created_at >= date_from)

    if date_to is not None:
        query = query.where(Sale.created_at <= date_to)

    if total_min is not None:
        query = query.where(Sale.total >= total_min)

    if total_max is not None:
        query = query.where(Sale.total <= total_max)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total_count = count_result.scalar_one()

    direction = Sale.created_at.asc() if order == "asc" else Sale.created_at.desc()
    query = query.order_by(direction).offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    return list(result.scalars().all()), total_count
