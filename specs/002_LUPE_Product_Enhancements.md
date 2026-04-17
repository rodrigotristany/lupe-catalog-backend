# Change Request: Product Enhancements

**Date:** 2026-04-16
**Author:** Rodrigo Tristany
**Status:** Pending Implementation

---

## Overview

This document specifies three changes to the product entity and its related behavior in the LUPE Catalog backend.

---

## 1. Cover Image Selection

### Description

Products can have multiple images stored in `product_images`. Currently there is no way to designate which image is used as the cover (primary) image displayed in listings.

### Changes

**`products` table**
- Add column `cover_image_id` (`Integer`, nullable, FK → `product_images.id`, `ON DELETE SET NULL`).

**`Product` model (`app/models/product.py`)**
- Add `cover_image_id` mapped column with the FK constraint above.
- Add a `cover_image` relationship to `ProductImage` (non-cascading, `lazy="selectin"`).

**Schemas (`app/schemas/`)**
- `ProductResponse`: expose `cover_image_id` and optionally the full `cover_image` object.
- `ProductUpdate`: allow `cover_image_id` to be set/changed (must belong to the same product).

**Service (`app/services/product_service.py`)**
- On update, validate that the provided `cover_image_id` belongs to the product being updated. Raise `400` if not.

**Admin router (`app/routers/admin.py`)**
- The existing `PATCH /api/v1/admin/products/{id}` endpoint handles this via the updated schema — no new route needed.

**Migration**
- `alembic revision --autogenerate -m "add cover_image_id to products"`

---

## 2. Product Display Priority

### Description

A numeric `priority` field is needed to control the order in which products are returned to the frontend. Lower values surface first (or alternatively higher values — to be confirmed at implementation time, but document the chosen convention in code).

### Changes

**`products` table**
- Add column `priority` (`Integer`, not null, default `0`).

**`Product` model (`app/models/product.py`)**
- Add `priority: Mapped[int]` with `server_default="0"`.
- Add an index `idx_products_priority` to support ordered queries.

**Schemas (`app/schemas/`)**
- `ProductResponse`: expose `priority`.
- `ProductCreate` / `ProductUpdate`: accept optional `priority` (defaults to `0` on create).

**Service (`app/services/product_service.py`)**
- Public listing queries (`get_products`, etc.) must `ORDER BY priority ASC` (lower = higher priority) as the primary sort, with a secondary `id ASC` tie-breaker.

**Migration**
- `alembic revision --autogenerate -m "add priority to products"`

---

## 3. Permanent Product Deletion

### Description

The current delete flow (`soft_delete_product`) sets `is_active = False` and retains the row. The new behavior must permanently remove the product row from the database.

### Changes

**Service (`app/services/product_service.py`)**
- Remove (or deprecate) `soft_delete_product`.
- Add `delete_product(db, product_id)` that issues a hard `DELETE` on the `products` row.
- Because `product_images` already has `ON DELETE CASCADE` and `product_history` has `cascade="all, delete-orphan"`, child records and image files on disk must also be cleaned up:
  - Collect image paths before deletion.
  - Delete the DB row (`await db.delete(product)`).
  - After flush, delete the image files from disk via `image_service`.

**Admin router (`app/routers/admin.py`)**
- Update `DELETE /api/v1/admin/products/{id}` to call `delete_product` instead of `soft_delete_product`.

**`Product` model / `is_active` field**
- `is_active` is kept as-is. It remains the mechanism to mark a product as out of stock or otherwise hidden without deleting it.

**Public queries**
- All existing `filter(Product.is_active == True)` guards remain unchanged.

---

---

## 4. Tests

All tests use the real `lupe_test` database following the existing `conftest.py` conventions (no mocks).

### 4.1 Cover Image

- `test_set_cover_image` — PATCH a product with a valid `cover_image_id` (one of its own images); assert `200` and `cover_image_id` is persisted.
- `test_set_cover_image_wrong_product` — PATCH with a `cover_image_id` that belongs to a different product; assert `400`.
- `test_cover_image_null_on_image_delete` — Delete the image that is set as cover; assert `cover_image_id` becomes `null` (FK `ON DELETE SET NULL`).
- `test_cover_image_in_response` — GET product; assert `cover_image_id` and `cover_image` are present in the response body.

### 4.2 Priority

- `test_priority_default_zero` — Create a product without specifying `priority`; assert `priority == 0` in response.
- `test_products_ordered_by_priority` — Create products with priorities `5`, `1`, `3`; GET list; assert returned order is `1 → 3 → 5`.
- `test_priority_tie_broken_by_id` — Create two products with the same `priority`; assert lower `id` comes first.
- `test_set_priority_on_create_and_update` — Create with `priority=10`, then PATCH to `priority=2`; assert both changes are reflected.

### 4.3 Permanent Deletion

- `test_delete_product_removes_row` — DELETE a product; assert subsequent GET returns `404` and the row is gone from the DB.
- `test_delete_product_removes_images_from_disk` — Upload images to a product, then DELETE it; assert image files no longer exist on disk.
- `test_delete_product_removes_history` — DELETE a product; assert its `product_history` rows are also gone.
- `test_delete_inactive_product` — DELETE a product with `is_active=False`; assert it is permanently removed (not just toggled).
- `test_delete_nonexistent_product` — DELETE a product ID that does not exist; assert `404`.

---

## Affected Files Summary

| File | Change |
|---|---|
| `app/models/product.py` | Add `cover_image_id`, `priority`; keep `is_active` |
| `app/models/product_image.py` | No structural change; FK target for `cover_image_id` |
| `app/schemas/product.py` | Expose new fields; accept on create/update |
| `app/services/product_service.py` | Validate cover image ownership; order by priority; hard delete |
| `app/routers/admin.py` | Wire delete route to new hard-delete service function |
| `alembic/versions/` | New migration(s) for schema changes |
| `tests/test_products.py` | New and updated test cases per section 4 |
