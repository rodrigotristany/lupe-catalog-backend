# Change Request: Sales Module

**Date:** 2026-06-13
**Author:** Rodrigo Tristany
**Status:** Pending Implementation

---

## Overview

This document specifies the Sales module for the LUPE Catalog admin dashboard. The feature consists of two sections: a sales list with filtering and ordering, and a form to record new sales. A single sale can contain multiple products, each tracked as a line item in the `sales_products` table. Payment methods are configured in the existing Settings section.

---

## 1. Database Schema

### 1.1 `sales` table (new)

The header record for a sale. Stores only sale-level data: payment method, stored total, and timestamp. Product details live in `sales_products`. Sales are immutable once created — no `updated_at` column.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | SERIAL | PK | Auto-increment primary key |
| payment_method | VARCHAR(100) | NOT NULL | Payment method label as recorded |
| total | DECIMAL(10,2) | NOT NULL, CHECK(total >= 0) | Stored sum of all line item subtotals |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Sale timestamp |

**Indexes:**
- `idx_sales_created_at` on `created_at`
- `idx_sales_payment_method` on `payment_method`

### 1.2 `sales_products` table (new)

One row per product line item within a sale. Product name, price, and category are captured as snapshots at the time of sale so the record survives future product edits or deletions.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | SERIAL | PK | Auto-increment primary key |
| sale_id | INTEGER | FK → sales.id, ON DELETE CASCADE, NOT NULL | Owning sale |
| product_id | INTEGER | FK → products.id, ON DELETE SET NULL, NULLABLE | Product reference (null if product is later deleted) |
| product_name_es | VARCHAR(255) | NOT NULL | Product name in Spanish at time of sale |
| product_name_en | VARCHAR(255) | NOT NULL | Product name in English at time of sale |
| category_id | INTEGER | NULLABLE | Category ID snapshot (plain integer, not a live FK) |
| category_name_es | VARCHAR(100) | NULLABLE | Category name in Spanish at time of sale |
| category_name_en | VARCHAR(100) | NULLABLE | Category name in English at time of sale |
| price | DECIMAL(10,2) | NOT NULL, CHECK(price >= 0) | Unit price at time of sale |
| quantity | INTEGER | NOT NULL, CHECK(quantity > 0) | Number of units for this line item |
| subtotal | DECIMAL(10,2) | NOT NULL, CHECK(subtotal >= 0) | Stored subtotal = price × quantity |

> `category_id` is a plain integer snapshot (not a FK) so the row survives category deletion. It is used only as a filter key on the list endpoint.

**Indexes:**
- `idx_sales_products_sale_id` on `sale_id`
- `idx_sales_products_product_id` on `product_id`
- `idx_sales_products_category_id` on `category_id`

### 1.3 `store_settings` table changes

Add one column to the existing single-row `store_settings` table to store the configurable list of payment methods.

| Column | Type | Constraints | Description |
|---|---|---|---|
| payment_methods | JSONB | NOT NULL, DEFAULT '[]' | Ordered list of payment method labels (array of strings) |

Example value: `["Efectivo", "Transferencia", "Mercado Pago"]`

---

## 2. SQLAlchemy Models

### 2.1 New model: `app/models/sale.py`

Defines both `Sale` and `SaleProduct` in a single file.

```python
from decimal import Decimal
from datetime import datetime
from sqlalchemy import String, Integer, DECIMAL, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (
        Index("idx_sales_created_at", "created_at"),
        Index("idx_sales_payment_method", "payment_method"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    payment_method: Mapped[str] = mapped_column(String(100), nullable=False)
    total: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    items: Mapped[list["SaleProduct"]] = relationship(
        "SaleProduct",
        back_populates="sale",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SaleProduct(Base):
    __tablename__ = "sales_products"
    __table_args__ = (
        Index("idx_sales_products_sale_id", "sale_id"),
        Index("idx_sales_products_product_id", "product_id"),
        Index("idx_sales_products_category_id", "category_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sales.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    product_name_es: Mapped[str] = mapped_column(String(255), nullable=False)
    product_name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category_name_es: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category_name_en: Mapped[str | None] = mapped_column(String(100), nullable=True)
    price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)

    sale: Mapped["Sale"] = relationship("Sale", back_populates="items")
```

### 2.2 Updated model: `app/models/store_settings.py`

Add the `payment_methods` column:

```python
from sqlalchemy import JSON
payment_methods: Mapped[list] = mapped_column(JSON, nullable=False, server_default="'[]'")
```

### 2.3 `app/models/__init__.py`

Import `Sale` and `SaleProduct` alongside existing models so Alembic detects them.

---

## 3. Pydantic Schemas

### 3.1 New file: `app/schemas/sale.py`

```python
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, field_validator


class SaleItemCreate(BaseModel):
    product_id: int
    quantity: int  # must be >= 1

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("quantity must be at least 1")
        return v


class SaleCreate(BaseModel):
    payment_method: str
    items: list[SaleItemCreate]  # must be non-empty; no duplicate product_id entries

    @field_validator("items")
    @classmethod
    def items_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("items must contain at least one product")
        return v


class SaleProductResponse(BaseModel):
    id: int
    product_id: int | None
    product_name_es: str
    product_name_en: str
    category_id: int | None
    category_name_es: str | None
    category_name_en: str | None
    price: Decimal
    quantity: int
    subtotal: Decimal

    model_config = {"from_attributes": True}


class SaleResponse(BaseModel):
    id: int
    payment_method: str
    total: Decimal
    created_at: datetime
    items: list[SaleProductResponse]

    model_config = {"from_attributes": True}


class SaleListParams(BaseModel):
    product_id: int | None = None       # matches any sale that contains this product
    category_id: int | None = None      # matches any sale with an item from this category
    payment_method: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    total_min: Decimal | None = None    # filter by sale total
    total_max: Decimal | None = None    # filter by sale total
    order: str = "desc"                 # "asc" or "desc" — always sorts by created_at
    page: int = 1
    per_page: int = 20                  # max 100
```

**Validation rules:**
- `SaleCreate.items`: non-empty list; duplicate `product_id` entries are rejected (`400`) at the service layer.
- `SaleItemCreate.quantity`: must be >= 1 (enforced in schema).
- `SaleCreate.payment_method`: validated against `store_settings.payment_methods` at the service layer (raise `400` if not found).
- `SaleListParams.order`: must be `"asc"` or `"desc"`.
- `SaleListParams.per_page`: max 100.

### 3.2 Updated: `app/schemas/settings.py`

Add `payment_methods` to both response and update schemas:

```python
# In SettingsResponse:
payment_methods: list[str] = []

# In SettingsUpdate:
payment_methods: list[str] | None = None
```

**Validation for `payment_methods` on update:**
- Each entry must be a non-empty string, max 100 characters.
- List max length: 20 methods.
- Duplicate entries are rejected (`400`).

---

## 4. Service Layer

### 4.1 New file: `app/services/sale_service.py`

```python
async def create_sale(db: AsyncSession, data: SaleCreate) -> Sale
async def get_sales(db: AsyncSession, params: SaleListParams) -> tuple[list[Sale], int]
```

#### `create_sale` logic

1. Fetch `StoreSettings` (id=1). Raise `400` if `data.payment_method` is not in `store_settings.payment_methods`.
2. Check for duplicate `product_id` entries in `data.items`. Raise `400` if any are found.
3. For each item in `data.items`:
   - Fetch the product by `product_id`. Raise `404` if not found.
   - Build a `SaleProduct` row capturing snapshot fields: `product_name_es`, `product_name_en`, `category_id`, `category_name_es`, `category_name_en` (from `product.category`, all nullable if product has no category), `price` from `product.price`.
   - Compute `subtotal = product.price * item.quantity`.
4. Compute `total = sum(sp.subtotal for sp in sale_products)`.
5. Create `Sale(payment_method=..., total=total)`, add all `SaleProduct` rows.
6. `db.add(sale)`, `await db.flush()`, `await db.refresh(sale)`.
7. Return the sale (items are eager-loaded via `lazy="selectin"`).

#### `get_sales` logic

Build a `SELECT` on `Sale` with optional filters. Filters that match against `sales_products` use an `EXISTS` subquery to avoid duplicating the sale row per item.

| Filter param | SQL condition |
|---|---|
| `product_id` | `EXISTS (SELECT 1 FROM sales_products sp WHERE sp.sale_id = Sale.id AND sp.product_id = :product_id)` |
| `category_id` | `EXISTS (SELECT 1 FROM sales_products sp WHERE sp.sale_id = Sale.id AND sp.category_id = :category_id)` |
| `payment_method` | `Sale.payment_method == payment_method` |
| `date_from` | `Sale.created_at >= date_from` |
| `date_to` | `Sale.created_at <= date_to` |
| `total_min` | `Sale.total >= total_min` |
| `total_max` | `Sale.total <= total_max` |

Ordering: always `ORDER BY Sale.created_at ASC/DESC` based on `params.order`.

Return `(items, total_count)` where `total_count` is a separate `SELECT COUNT(*)` with the same filters applied (no pagination).

### 4.2 Updated: `app/services/settings_service.py`

No new logic needed. The `payment_methods` field is handled automatically once the schema and model are updated.

---

## 5. API Endpoints

All new sales endpoints live under `/api/v1/admin/sales` and require JWT auth (`get_current_admin` dependency).

### 5.1 `POST /api/v1/admin/sales`

Create a new sale with one or more product line items.

**Request body:**

```json
{
  "payment_method": "Transferencia",
  "items": [
    { "product_id": 15, "quantity": 2 },
    { "product_id": 3, "quantity": 1 }
  ]
}
```

**Response 201:**

```json
{
  "id": 1,
  "payment_method": "Transferencia",
  "total": "68.00",
  "created_at": "2026-06-13T14:30:00Z",
  "items": [
    {
      "id": 1,
      "product_id": 15,
      "product_name_es": "Canasta Tejida",
      "product_name_en": "Handwoven Basket",
      "category_id": 3,
      "category_name_es": "Cestas",
      "category_name_en": "Baskets",
      "price": "25.00",
      "quantity": 2,
      "subtotal": "50.00"
    },
    {
      "id": 2,
      "product_id": 3,
      "product_name_es": "Taza de Barro",
      "product_name_en": "Clay Mug",
      "category_id": 1,
      "category_name_es": "Cerámica",
      "category_name_en": "Ceramics",
      "price": "18.00",
      "quantity": 1,
      "subtotal": "18.00"
    }
  ]
}
```

**Error cases:**

| Status | Condition |
|---|---|
| 400 | `payment_method` not in `store_settings.payment_methods` |
| 400 | Duplicate `product_id` entries in `items` |
| 404 | Any `product_id` in `items` not found |
| 422 | `items` is empty, or any `quantity` < 1 |

### 5.2 `GET /api/v1/admin/sales`

Returns a paginated, filtered list of sales. Each sale includes its full `items` array.

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| product_id | int | (none) | Match sales that contain this product |
| category_id | int | (none) | Match sales that contain an item from this category |
| payment_method | string | (none) | Exact match on payment method label |
| date_from | ISO 8601 datetime | (none) | Lower bound on `created_at` (inclusive) |
| date_to | ISO 8601 datetime | (none) | Upper bound on `created_at` (inclusive) |
| total_min | decimal | (none) | Lower bound on sale total |
| total_max | decimal | (none) | Upper bound on sale total |
| order | string | `desc` | Sort direction for `created_at`: `asc` or `desc` |
| page | int | 1 | Page number |
| per_page | int | 20 | Items per page (max 100) |

**Response 200:**

```json
{
  "items": [
    {
      "id": 1,
      "payment_method": "Transferencia",
      "total": "68.00",
      "created_at": "2026-06-13T14:30:00Z",
      "items": [
        {
          "id": 1,
          "product_id": 15,
          "product_name_es": "Canasta Tejida",
          "product_name_en": "Handwoven Basket",
          "category_id": 3,
          "category_name_es": "Cestas",
          "category_name_en": "Baskets",
          "price": "25.00",
          "quantity": 2,
          "subtotal": "50.00"
        }
      ]
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 20,
  "pages": 1
}
```

### 5.3 Product search for the sale form

The sale creation form needs a searchable product selector. Re-use the existing endpoint:

```
GET /api/v1/admin/products?search=<text>&per_page=20
```

No new endpoint needed. The frontend sends the user's typed text as `search` and populates the dropdown with `name_es`, `name_en`, `price`, and `category`. When a product is selected, the form displays the price for the admin's reference — the actual price is read server-side on `POST /admin/sales`.

The form allows the admin to add multiple product rows before submitting. All rows are sent together as the `items` array in a single `POST`.

### 5.4 Settings — payment methods

Payment methods are managed via the existing settings endpoint with the new field.

**`PUT /api/v1/admin/settings`:**

```json
{
  "payment_methods": ["Efectivo", "Transferencia", "Mercado Pago"]
}
```

**`GET /api/v1/admin/settings`** response now includes:

```json
{
  "store_name": "LUPE",
  "whatsapp_number": "+5493534000000",
  "currency_symbol": "$",
  "default_language": "es",
  "payment_methods": ["Efectivo", "Transferencia", "Mercado Pago"]
}
```

The sale form fetches this endpoint to populate the payment method `<select>`.

---

## 6. Admin Router Changes

### `app/routers/admin.py`

Add the two new sales routes:

```python
from app.services import sale_service
from app.schemas.sale import SaleCreate, SaleResponse, SaleListParams

@router.post("/sales", response_model=SaleResponse, status_code=201)
async def create_sale(data: SaleCreate, db=Depends(get_db), _=Depends(get_current_admin)):
    return await sale_service.create_sale(db, data)

@router.get("/sales", response_model=PaginatedResponse[SaleResponse])
async def list_sales(params: SaleListParams = Depends(), db=Depends(get_db), _=Depends(get_current_admin)):
    items, total = await sale_service.get_sales(db, params)
    return build_paginated_response(items, total, params.page, params.per_page)
```

---

## 7. Migration

```bash
alembic revision --autogenerate -m "add sales and sales_products tables and payment_methods to store_settings"
alembic upgrade head
```

The migration must:
1. Create the `sales` table (Section 1.1).
2. Create the `sales_products` table (Section 1.2).
3. Add `payment_methods JSONB NOT NULL DEFAULT '[]'` to `store_settings`.

---

## 8. Tests

All tests use the real `lupe_test` database following existing `conftest.py` conventions. Add a new file `tests/test_sales.py`.

### 8.1 Create sale

- `test_create_sale_single_item` — POST with one item; assert `201`, correct `total`, `subtotal`, and all snapshot fields in the response.
- `test_create_sale_multiple_items` — POST with two items; assert `total` equals the sum of both `subtotal` values; assert both items are in `response["items"]`.
- `test_create_sale_snapshots_product_data` — POST a sale, then update the product's price; GET the sale list; assert `price` on the sale item still reflects the original price.
- `test_create_sale_product_not_found` — POST with a non-existent `product_id` in items; assert `404`.
- `test_create_sale_invalid_payment_method` — POST with a `payment_method` not in `store_settings.payment_methods`; assert `400`.
- `test_create_sale_empty_items` — POST with `items=[]`; assert `422`.
- `test_create_sale_duplicate_product_id` — POST with the same `product_id` appearing twice in `items`; assert `400`.
- `test_create_sale_quantity_zero` — POST with `quantity=0` on any item; assert `422`.
- `test_create_sale_item_no_category` — POST for a product with no category; assert the sale item has `category_id=null` and `category_name_es/en=null`.
- `test_create_sale_subtotal_computed` — POST with `price=25.00` (from product) and `quantity=3`; assert `subtotal="75.00"`.
- `test_create_sale_total_is_sum_of_subtotals` — POST with two items; assert `sale.total == item1.subtotal + item2.subtotal`.

### 8.2 List sales

- `test_list_sales_empty` — GET with no sales in DB; assert `total=0` and `items=[]`.
- `test_list_sales_all` — Create 3 sales; GET; assert all 3 returned ordered by `created_at DESC` (default); each includes its `items` array.
- `test_list_sales_order_asc` — GET with `order=asc`; assert chronological order.
- `test_list_sales_filter_by_product_id` — Create two sales with different products; filter by one `product_id`; assert only the matching sale is returned.
- `test_list_sales_filter_by_product_id_multi_item_sale` — Create a sale with two products; filter by one of the product IDs; assert the sale is returned.
- `test_list_sales_filter_by_category_id` — Create sales with items from different categories; filter by category; assert correct results.
- `test_list_sales_filter_by_payment_method` — Create sales with different methods; filter; assert only matching sales returned.
- `test_list_sales_filter_by_date_range` — Create sales at different timestamps; filter with `date_from` and `date_to`; assert boundary inclusivity.
- `test_list_sales_filter_by_total_range` — Create sales with different totals; filter with `total_min` and `total_max`; assert correct results.
- `test_list_sales_combined_filters` — Apply two filters simultaneously; assert intersection.
- `test_list_sales_pagination` — Create 25 sales; GET page 1 (`per_page=20`) and page 2; assert correct slices and `total=25`, `pages=2`.

### 8.3 Payment methods in settings

- `test_settings_payment_methods_default_empty` — Fresh seed creates `store_settings` with `payment_methods=[]`; GET settings; assert field is present and empty.
- `test_update_payment_methods` — PUT settings with `payment_methods=["Efectivo", "Transferencia"]`; GET; assert persisted.
- `test_update_payment_methods_duplicates_rejected` — PUT with `["Efectivo", "Efectivo"]`; assert `400`.
- `test_update_payment_methods_empty_string_rejected` — PUT with `[""]`; assert `400`.
- `test_sale_payment_method_validates_against_settings` — Set methods to `["Efectivo"]`; POST sale with `"Transferencia"`; assert `400`.

### 8.4 Product deletion does not break sale history

- `test_sale_survives_product_deletion` — Create a sale with two items, then DELETE one product; GET the sale list; assert the sale still exists, the deleted item has `product_id=null`, and all snapshot fields are intact.

---

## 9. Seed Script Updates

In `scripts/seed.py`, update the `store_settings` row creation to include `payment_methods`:

```python
payment_methods=["Efectivo", "Transferencia", "Mercado Pago"]
```

---

## 10. Affected Files Summary

| File | Change |
|---|---|
| `app/models/sale.py` | New — `Sale` and `SaleProduct` ORM models |
| `app/models/store_settings.py` | Add `payment_methods` JSONB column |
| `app/models/__init__.py` | Import `Sale`, `SaleProduct` |
| `app/schemas/sale.py` | New — `SaleItemCreate`, `SaleCreate`, `SaleProductResponse`, `SaleResponse`, `SaleListParams` |
| `app/schemas/settings.py` | Add `payment_methods` to `SettingsResponse` and `SettingsUpdate` |
| `app/services/sale_service.py` | New — `create_sale`, `get_sales` |
| `app/routers/admin.py` | Add `POST /sales` and `GET /sales` routes |
| `alembic/versions/` | New migration: `sales`, `sales_products` tables + `payment_methods` column |
| `scripts/seed.py` | Seed `payment_methods` in `store_settings` |
| `tests/test_sales.py` | New — all test cases from Section 8 |
