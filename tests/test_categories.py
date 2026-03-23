import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.category import Category
from app.models.product import Product


@pytest.mark.asyncio
async def test_list_categories_empty(client: AsyncClient):
    resp = await client.get("/api/v1/categories")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_category(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/admin/categories",
        json={"name_es": "Cerámica", "name_en": "Ceramics"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name_es"] == "Cerámica"
    assert data["name_en"] == "Ceramics"
    assert data["slug"] == "ceramics"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_category_duplicate_slug(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/v1/admin/categories",
        json={"name_es": "Cerámica", "name_en": "Ceramics"},
        headers=auth_headers,
    )
    resp = await client.post(
        "/api/v1/admin/categories",
        json={"name_es": "Another", "name_en": "Ceramics"},
        headers=auth_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_categories(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/v1/admin/categories",
        json={"name_es": "Textiles", "name_en": "Textiles"},
        headers=auth_headers,
    )
    resp = await client.get("/api/v1/categories")
    assert resp.status_code == 200
    slugs = [c["slug"] for c in resp.json()]
    assert "textiles" in slugs


@pytest.mark.asyncio
async def test_update_category_slug_regenerated(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post(
        "/api/v1/admin/categories",
        json={"name_es": "Cestas", "name_en": "Baskets"},
        headers=auth_headers,
    )
    cat_id = create_resp.json()["id"]
    update_resp = await client.put(
        f"/api/v1/admin/categories/{cat_id}",
        json={"name_en": "Wicker Baskets"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["slug"] == "wicker-baskets"


@pytest.mark.asyncio
async def test_delete_category_sets_product_category_null(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    # Create category
    cat_resp = await client.post(
        "/api/v1/admin/categories",
        json={"name_es": "Joyería", "name_en": "Jewelry"},
        headers=auth_headers,
    )
    cat_id = cat_resp.json()["id"]

    # Create product in that category
    prod_resp = await client.post(
        "/api/v1/admin/products",
        json={"name_es": "Anillo", "name_en": "Ring", "price": 10.00, "category_id": cat_id},
        headers=auth_headers,
    )
    prod_id = prod_resp.json()["id"]

    # Delete category
    del_resp = await client.delete(f"/api/v1/admin/categories/{cat_id}", headers=auth_headers)
    assert del_resp.status_code == 200

    # Product's category_id should be NULL
    result = await db_session.execute(select(Product).where(Product.id == prod_id))
    product = result.scalar_one()
    assert product.category_id is None


@pytest.mark.asyncio
async def test_delete_category_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.delete("/api/v1/admin/categories/999999", headers=auth_headers)
    assert resp.status_code == 404
