import io
import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.product import Product
from app.models.product_history import ProductHistory


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), color=(100, 150, 200)).save(buf, format="JPEG")
    return buf.getvalue()


async def _create_product(client, auth_headers, **kwargs) -> dict:
    payload = {"name_es": "Producto", "name_en": "Product", "price": 10.00, **kwargs}
    resp = await client.post("/api/v1/admin/products", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


async def _upload_image(client, auth_headers, product_id: int) -> dict:
    resp = await client.post(
        f"/api/v1/admin/products/{product_id}/images",
        files={"images": ("img.jpg", _make_jpeg_bytes(), "image/jpeg")},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()[0]


# ── Basic CRUD ─────────────────────────────────────────────────────────────────

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
    assert history[0]["action"] == "updated"
    assert history[1]["action"] == "created"


# ── Cover Image ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_set_cover_image(client: AsyncClient, auth_headers: dict):
    product = await _create_product(client, auth_headers)
    prod_id = product["id"]
    img = await _upload_image(client, auth_headers, prod_id)

    resp = await client.put(
        f"/api/v1/admin/products/{prod_id}",
        json={"cover_image_id": img["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cover_image_id"] == img["id"]
    assert data["cover_image"]["id"] == img["id"]


@pytest.mark.asyncio
async def test_set_cover_image_wrong_product(client: AsyncClient, auth_headers: dict):
    prod_a = await _create_product(client, auth_headers, name_es="A", name_en="A")
    prod_b = await _create_product(client, auth_headers, name_es="B", name_en="B")
    img = await _upload_image(client, auth_headers, prod_b["id"])

    resp = await client.put(
        f"/api/v1/admin/products/{prod_a['id']}",
        json={"cover_image_id": img["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_cover_image_null_on_image_delete(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    product = await _create_product(client, auth_headers)
    prod_id = product["id"]
    img = await _upload_image(client, auth_headers, prod_id)
    img_id = img["id"]

    await client.put(
        f"/api/v1/admin/products/{prod_id}",
        json={"cover_image_id": img_id},
        headers=auth_headers,
    )

    await client.delete(f"/api/v1/admin/images/{img_id}", headers=auth_headers)

    await db_session.expire_all()
    result = await db_session.execute(select(Product).where(Product.id == prod_id))
    product_row = result.scalar_one()
    assert product_row.cover_image_id is None


@pytest.mark.asyncio
async def test_cover_image_in_response(client: AsyncClient, auth_headers: dict):
    product = await _create_product(client, auth_headers)
    prod_id = product["id"]

    resp = await client.get(f"/api/v1/products/{prod_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "cover_image_id" in data
    assert "cover_image" in data
    assert data["cover_image_id"] is None
    assert data["cover_image"] is None


# ── Priority ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_priority_default_zero(client: AsyncClient, auth_headers: dict):
    product = await _create_product(client, auth_headers)
    assert product["priority"] == 0


@pytest.mark.asyncio
async def test_products_ordered_by_priority(client: AsyncClient, auth_headers: dict):
    await _create_product(client, auth_headers, name_es="P5", name_en="P5", priority=5)
    await _create_product(client, auth_headers, name_es="P1", name_en="P1", priority=1)
    await _create_product(client, auth_headers, name_es="P3", name_en="P3", priority=3)

    resp = await client.get("/api/v1/products")
    assert resp.status_code == 200
    priorities = [p["priority"] for p in resp.json()["items"]]
    assert priorities == sorted(priorities)


@pytest.mark.asyncio
async def test_priority_tie_broken_by_id(client: AsyncClient, auth_headers: dict):
    p1 = await _create_product(client, auth_headers, name_es="First", name_en="First", priority=5)
    p2 = await _create_product(client, auth_headers, name_es="Second", name_en="Second", priority=5)

    resp = await client.get("/api/v1/products")
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()["items"]]
    assert ids.index(p1["id"]) < ids.index(p2["id"])


@pytest.mark.asyncio
async def test_set_priority_on_create_and_update(client: AsyncClient, auth_headers: dict):
    product = await _create_product(client, auth_headers, priority=10)
    assert product["priority"] == 10

    resp = await client.put(
        f"/api/v1/admin/products/{product['id']}",
        json={"priority": 2},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["priority"] == 2


# ── Permanent Deletion ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_product_removes_row(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    product = await _create_product(client, auth_headers)
    prod_id = product["id"]

    resp = await client.delete(f"/api/v1/admin/products/{prod_id}", headers=auth_headers)
    assert resp.status_code == 200

    assert (await client.get(f"/api/v1/products/{prod_id}")).status_code == 404

    await db_session.expire_all()
    result = await db_session.execute(select(Product).where(Product.id == prod_id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_product_removes_images_from_disk(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    from unittest.mock import AsyncMock
    deleted_paths = []

    async def capture_delete(path):
        deleted_paths.append(path)

    monkeypatch.setattr("app.services.product_service.storage_service.delete", capture_delete)

    product = await _create_product(client, auth_headers)
    prod_id = product["id"]
    img = await _upload_image(client, auth_headers, prod_id)

    await client.delete(f"/api/v1/admin/products/{prod_id}", headers=auth_headers)

    assert img["image_path"] in deleted_paths


@pytest.mark.asyncio
async def test_delete_product_removes_history(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    product = await _create_product(client, auth_headers)
    prod_id = product["id"]

    await client.delete(f"/api/v1/admin/products/{prod_id}", headers=auth_headers)

    await db_session.expire_all()
    result = await db_session.execute(
        select(ProductHistory).where(ProductHistory.product_id == prod_id)
    )
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_delete_inactive_product(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    product = await _create_product(client, auth_headers, is_active=False)
    prod_id = product["id"]

    resp = await client.delete(f"/api/v1/admin/products/{prod_id}", headers=auth_headers)
    assert resp.status_code == 200

    await db_session.expire_all()
    result = await db_session.execute(select(Product).where(Product.id == prod_id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_nonexistent_product(client: AsyncClient, auth_headers: dict):
    resp = await client.delete("/api/v1/admin/products/999999", headers=auth_headers)
    assert resp.status_code == 404
