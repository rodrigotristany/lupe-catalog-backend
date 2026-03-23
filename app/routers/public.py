import math
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.services import category_service, product_service, settings_service
from app.schemas.category import CategoryResponse
from app.schemas.product import ProductListItem, ProductDetail
from app.schemas.settings import SettingsResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/api/v1")


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    categories = await category_service.get_all_categories(db)
    return categories


@router.get("/products", response_model=PaginatedResponse[ProductListItem])
async def list_products(
    category: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort: str = Query("created_at"),
    order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
):
    products, total = await product_service.get_products(
        db,
        category_slug=category,
        search=search,
        page=page,
        per_page=per_page,
        sort=sort,
        order=order,
        include_inactive=False,
    )
    items = [_to_list_item(p) for p in products]
    pages = math.ceil(total / per_page) if total > 0 else 0
    return PaginatedResponse(items=items, total=total, page=page, per_page=per_page, pages=pages)


@router.get("/products/{product_id}", response_model=ProductDetail)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    product = await product_service.get_product_by_id(db, product_id)
    return _to_detail(product)


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    return await settings_service.get_settings(db)


def _to_list_item(product) -> ProductListItem:
    primary_image = product.images[0].image_path if product.images else None
    return ProductListItem(
        id=product.id,
        name_es=product.name_es,
        name_en=product.name_en,
        description_es=product.description_es,
        description_en=product.description_en,
        price=str(product.price),
        category=product.category,
        primary_image=primary_image,
        is_active=product.is_active,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _to_detail(product) -> ProductDetail:
    return ProductDetail(
        id=product.id,
        name_es=product.name_es,
        name_en=product.name_en,
        description_es=product.description_es,
        description_en=product.description_en,
        price=str(product.price),
        category=product.category,
        images=product.images,
        is_active=product.is_active,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )
