import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.product_history import ProductHistory


@pytest.mark.asyncio
async def test_list_products_empty(client: AsyncClient):
    resp = await client.get("/api/v1/products")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_create_product(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/admin/products",
        json={"name_es": "Canasta Tejida", "name_en": "Woven Basket", "price": 25.00},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name_es"] == "Canasta Tejida"
    assert data["price"] == "25.00"
    assert data["is_active"] is True
    assert data["images"] == []


@pytest.mark.asyncio
async def test_create_product_creates_history(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    resp = await client.post(
        "/api/v1/admin/products",
        json={"name_es": "Taza", "name_en": "Mug", "price": 10.00},
        headers=auth_headers,
    )
    prod_id = resp.json()["id"]
    result = await db_session.execute(
        select(ProductHistory).where(ProductHistory.product_id == prod_id)
    )
    history = result.scalars().all()
    assert len(history) == 1
    assert history[0].action == "created"


@pytest.mark.asyncio
async def test_create_product_invalid_price(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/admin/products",
        json={"name_es": "Test", "name_en": "Test", "price": -1},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_product(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/admin/products",
        json={"name_es": "Plato", "name_en": "Plate", "price": 15.00},
        headers=auth_headers,
    )
    prod_id = create.json()["id"]
    resp = await client.get(f"/api/v1/products/{prod_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == prod_id


@pytest.mark.asyncio
async def test_get_inactive_product_returns_404(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/admin/products",
        json={"name_es": "Plato", "name_en": "Plate", "price": 15.00, "is_active": False},
        headers=auth_headers,
    )
    prod_id = create.json()["id"]
    resp = await client.get(f"/api/v1/products/{prod_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_product(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    create = await client.post(
        "/api/v1/admin/products",
        json={"name_es": "Jarra", "name_en": "Jug", "price": 30.00},
        headers=auth_headers,
    )
    prod_id = create.json()["id"]

    update = await client.put(
        f"/api/v1/admin/products/{prod_id}",
        json={"price": 35.00},
        headers=auth_headers,
    )
    assert update.status_code == 200
    assert update.json()["price"] == "35.00"

    # Verify history
    result = await db_session.execute(
        select(ProductHistory)
        .where(ProductHistory.product_id == prod_id)
        .order_by(ProductHistory.changed_at)
    )
    history = result.scalars().all()
    assert len(history) == 2
    assert history[0].action == "created"
    assert history[1].action == "updated"
    assert history[1].snapshot["price"] == "35.00"


@pytest.mark.asyncio
async def test_soft_delete_product(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    create = await client.post(
        "/api/v1/admin/products",
        json={"name_es": "Vaso", "name_en": "Glass", "price": 8.00},
        headers=auth_headers,
    )
    prod_id = create.json()["id"]

    delete = await client.delete(f"/api/v1/admin/products/{prod_id}", headers=auth_headers)
    assert delete.status_code == 200
    assert "soft" in delete.json()["detail"]

    # Product is gone from public API
    resp = await client.get(f"/api/v1/products/{prod_id}")
    assert resp.status_code == 404

    # But admin can still see it
    admin_list = await client.get("/api/v1/admin/products", headers=auth_headers)
    ids = [p["id"] for p in admin_list.json()["items"]]
    assert prod_id in ids

    # History has deleted action
    result = await db_session.execute(
        select(ProductHistory)
        .where(ProductHistory.product_id == prod_id)
        .order_by(ProductHistory.changed_at.desc())
    )
    history = result.scalars().all()
    assert history[0].action == "deleted"


@pytest.mark.asyncio
async def test_list_products_pagination(client: AsyncClient, auth_headers: dict):
    for i in range(5):
        await client.post(
            "/api/v1/admin/products",
            json={"name_es": f"Prod ES {i}", "name_en": f"Prod EN {i}", "price": float(i + 1)},
            headers=auth_headers,
        )
    resp = await client.get("/api/v1/products?page=1&per_page=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] >= 5
    assert data["pages"] >= 3


@pytest.mark.asyncio
async def test_list_products_search(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/v1/admin/products",
        json={"name_es": "Canasta Única", "name_en": "Unique Basket", "price": 20.00},
        headers=auth_headers,
    )
    resp = await client.get("/api/v1/products?search=unique")
    assert resp.status_code == 200
    names = [p["name_en"] for p in resp.json()["items"]]
    assert "Unique Basket" in names


@pytest.mark.asyncio
async def test_product_history_endpoint(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/admin/products",
        json={"name_es": "Vasija", "name_en": "Vessel", "price": 50.00},
        headers=auth_headers,
    )
    prod_id = create.json()["id"]
    await client.put(
        f"/api/v1/admin/products/{prod_id}",
        json={"price": 55.00},
        headers=auth_headers,
    )
    resp = await client.get(f"/api/v1/admin/products/{prod_id}/history", headers=auth_headers)
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) == 2
    # Newest first
    assert history[0]["action"] == "updated"
    assert history[1]["action"] == "created"
