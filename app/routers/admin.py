import math
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, Query, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_admin
from app.services import (
    auth_service,
    category_service,
    product_service,
    image_service,
    settings_service,
    sale_service,
)
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductDetail,
    ProductListItem,
    ProductHistoryResponse,
    ProductImageResponse,
)
from app.schemas.settings import SettingsResponse, SettingsUpdate
from app.schemas.sale import SaleCreate, SaleResponse
from app.schemas.common import PaginatedResponse
from app.config import settings as app_settings
from fastapi import HTTPException

router = APIRouter(prefix="/api/v1/admin")


# ── Auth ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    token = await auth_service.authenticate_admin(db, body.username, body.password)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=app_settings.JWT_EXPIRATION_MINUTES,
    )


# ── Categories ────────────────────────────────────────────────────────────────

@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    return await category_service.get_all_categories(db)


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    return await category_service.create_category(db, body)


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    body: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    return await category_service.update_category(db, category_id, body)


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    await category_service.delete_category(db, category_id)
    return {"detail": "Category deleted"}


# ── Products ─────────────────────────────────────────────────────────────────

@router.get("/products", response_model=PaginatedResponse[ProductListItem])
async def list_products(
    category: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort: str = Query("created_at"),
    order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    products, total = await product_service.get_products(
        db,
        category_slug=category,
        search=search,
        page=page,
        per_page=per_page,
        sort=sort,
        order=order,
        include_inactive=True,
    )
    items = [_to_list_item(p) for p in products]
    pages = math.ceil(total / per_page) if total > 0 else 0
    return PaginatedResponse(items=items, total=total, page=page, per_page=per_page, pages=pages)


@router.post("/products", response_model=ProductDetail, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    product = await product_service.create_product(db, body, username=admin)
    return _to_detail(product)


@router.put("/products/{product_id}", response_model=ProductDetail)
async def update_product(
    product_id: int,
    body: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    product = await product_service.update_product(db, product_id, body, username=admin)
    return _to_detail(product)


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    await product_service.delete_product(db, product_id)
    return {"detail": "Product deleted"}


@router.post(
    "/products/{product_id}/images",
    response_model=list[ProductImageResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_images(
    product_id: int,
    images: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    product = await product_service.get_product_by_id(db, product_id, include_inactive=True)
    created = await image_service.upload_images(db, product, images, username=admin)
    # Save history snapshot after upload
    await product_service._save_snapshot(db, product, "updated", admin)
    return [
        ProductImageResponse(
            id=img.id,
            image_path=img.image_path,
            image_url=app_settings.image_url(img.image_path),
            sort_order=img.sort_order,
        )
        for img in created
    ]


@router.get("/products/{product_id}/history", response_model=list[ProductHistoryResponse])
async def get_product_history(
    product_id: int,
    limit: int | None = Query(None, ge=1),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    return await product_service.get_product_history(db, product_id, limit=limit)


# ── Images ────────────────────────────────────────────────────────────────────

@router.delete("/images/{image_id}")
async def delete_image(
    image_id: int,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    product = await image_service.delete_image(db, image_id)
    await product_service._save_snapshot(db, product, "updated", admin)
    return {"detail": "Image deleted"}


# ── Settings ─────────────────────────────────────────────────────────────────

@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    return await settings_service.get_settings(db)


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    body: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    return await settings_service.update_settings(db, body)


# ── Sales ─────────────────────────────────────────────────────────────────────

@router.post("/sales", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
async def create_sale(
    body: SaleCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    return await sale_service.create_sale(db, body)


@router.get("/sales", response_model=PaginatedResponse[SaleResponse])
async def list_sales(
    product_id: int | None = Query(None),
    category_id: int | None = Query(None),
    payment_method: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    total_min: Decimal | None = Query(None),
    total_max: Decimal | None = Query(None),
    order: str = Query("desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    sales, total = await sale_service.get_sales(
        db,
        product_id=product_id,
        category_id=category_id,
        payment_method=payment_method,
        date_from=date_from,
        date_to=date_to,
        total_min=total_min,
        total_max=total_max,
        order=order,
        page=page,
        per_page=per_page,
    )
    pages = math.ceil(total / per_page) if total > 0 else 0
    return PaginatedResponse(items=sales, total=total, page=page, per_page=per_page, pages=pages)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_list_item(product) -> ProductListItem:
    cover = product.cover_image or (product.images[0] if product.images else None)
    primary_image = app_settings.image_url(cover.image_path) if cover else None
    return ProductListItem(
        id=product.id,
        name_es=product.name_es,
        name_en=product.name_en,
        description_es=product.description_es,
        description_en=product.description_en,
        price=str(product.price),
        category=product.category,
        primary_image=primary_image,
        cover_image_id=product.cover_image_id,
        is_active=product.is_active,
        priority=product.priority,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _to_detail(product) -> ProductDetail:
    cover = (
        ProductImageResponse(
            id=product.cover_image.id,
            image_path=product.cover_image.image_path,
            image_url=app_settings.image_url(product.cover_image.image_path),
            sort_order=product.cover_image.sort_order,
        )
        if product.cover_image
        else None
    )
    return ProductDetail(
        id=product.id,
        name_es=product.name_es,
        name_en=product.name_en,
        description_es=product.description_es,
        description_en=product.description_en,
        price=str(product.price),
        category=product.category,
        images=[
            ProductImageResponse(
                id=img.id,
                image_path=img.image_path,
                image_url=app_settings.image_url(img.image_path),
                sort_order=img.sort_order,
            )
            for img in product.images
        ],
        cover_image_id=product.cover_image_id,
        cover_image=cover,
        is_active=product.is_active,
        priority=product.priority,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )
