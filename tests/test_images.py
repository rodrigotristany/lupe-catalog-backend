import io
import pytest
from httpx import AsyncClient
from PIL import Image as PILImage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.product_history import ProductHistory


def make_jpeg_bytes(width: int = 100, height: int = 100) -> bytes:
    img = PILImage.new("RGB", (width, height), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def make_png_bytes() -> bytes:
    img = PILImage.new("RGB", (50, 50), color=(0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def _create_product(client: AsyncClient, auth_headers: dict) -> int:
    resp = await client.post(
        "/api/v1/admin/products",
        json={"name_es": "Img Test", "name_en": "Img Test", "price": 10.00},
        headers=auth_headers,
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_upload_single_image(client: AsyncClient, auth_headers: dict):
    prod_id = await _create_product(client, auth_headers)
    resp = await client.post(
        f"/api/v1/admin/products/{prod_id}/images",
        files=[("files", ("test.jpg", make_jpeg_bytes(), "image/jpeg"))],
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 1
    assert data[0]["sort_order"] == 0
    assert "products/" in data[0]["image_path"]


@pytest.mark.asyncio
async def test_upload_multiple_images(client: AsyncClient, auth_headers: dict):
    prod_id = await _create_product(client, auth_headers)
    resp = await client.post(
        f"/api/v1/admin/products/{prod_id}/images",
        files=[
            ("files", ("a.jpg", make_jpeg_bytes(), "image/jpeg")),
            ("files", ("b.png", make_png_bytes(), "image/png")),
        ],
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 2
    assert data[0]["sort_order"] == 0
    assert data[1]["sort_order"] == 1


@pytest.mark.asyncio
async def test_upload_invalid_format(client: AsyncClient, auth_headers: dict):
    prod_id = await _create_product(client, auth_headers)
    resp = await client.post(
        f"/api/v1/admin/products/{prod_id}/images",
        files=[("files", ("doc.pdf", b"%PDF-1.4 fake", "application/pdf"))],
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_oversized_file(client: AsyncClient, auth_headers: dict):
    prod_id = await _create_product(client, auth_headers)
    # 6 MB of zeros, but content-type set to image/jpeg
    big_data = b"\x00" * (6 * 1024 * 1024)
    resp = await client.post(
        f"/api/v1/admin/products/{prod_id}/images",
        files=[("files", ("big.jpg", big_data, "image/jpeg"))],
        headers=auth_headers,
    )
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_delete_image(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    prod_id = await _create_product(client, auth_headers)
    upload = await client.post(
        f"/api/v1/admin/products/{prod_id}/images",
        files=[("files", ("img.jpg", make_jpeg_bytes(), "image/jpeg"))],
        headers=auth_headers,
    )
    image_id = upload.json()[0]["id"]

    del_resp = await client.delete(f"/api/v1/admin/images/{image_id}", headers=auth_headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["detail"] == "Image deleted"

    # History should have an 'updated' entry after deletion
    result = await db_session.execute(
        select(ProductHistory)
        .where(ProductHistory.product_id == prod_id)
        .order_by(ProductHistory.changed_at.desc())
    )
    history = result.scalars().all()
    actions = [h.action for h in history]
    assert "updated" in actions


@pytest.mark.asyncio
async def test_image_upload_creates_history(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    prod_id = await _create_product(client, auth_headers)
    await client.post(
        f"/api/v1/admin/products/{prod_id}/images",
        files=[("files", ("img.jpg", make_jpeg_bytes(), "image/jpeg"))],
        headers=auth_headers,
    )
    result = await db_session.execute(
        select(ProductHistory)
        .where(ProductHistory.product_id == prod_id)
        .order_by(ProductHistory.changed_at.desc())
    )
    history = result.scalars().all()
    # Should have: created + updated (from image upload)
    assert len(history) >= 2
    actions = [h.action for h in history]
    assert "updated" in actions
