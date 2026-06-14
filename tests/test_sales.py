import pytest
from httpx import AsyncClient


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _create_product(client: AsyncClient, auth_headers: dict, **kwargs) -> dict:
    payload = {"name_es": "Producto", "name_en": "Product", "price": 10.00, **kwargs}
    resp = await client.post("/api/v1/admin/products", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


async def _create_category(client: AsyncClient, auth_headers: dict, name_es: str = "Cat", name_en: str = "Cat") -> dict:
    resp = await client.post(
        "/api/v1/admin/categories",
        json={"name_es": name_es, "name_en": name_en},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_sale(client: AsyncClient, auth_headers: dict, items: list[dict], payment_method: str = "Efectivo") -> dict:
    resp = await client.post(
        "/api/v1/admin/sales",
        json={"payment_method": payment_method, "items": items},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()


# ── Create sale ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_sale_single_item(client: AsyncClient, auth_headers: dict):
    product = await _create_product(client, auth_headers, price=25.00)
    sale = await _create_sale(client, auth_headers, [{"product_id": product["id"], "quantity": 2}])

    assert sale["payment_method"] == "Efectivo"
    assert sale["total"] == "50.00"
    assert len(sale["items"]) == 1
    item = sale["items"][0]
    assert item["product_id"] == product["id"]
    assert item["product_name_es"] == product["name_es"]
    assert item["price"] == "25.00"
    assert item["quantity"] == 2
    assert item["subtotal"] == "50.00"


@pytest.mark.asyncio
async def test_create_sale_multiple_items(client: AsyncClient, auth_headers: dict):
    p1 = await _create_product(client, auth_headers, name_es="P1", name_en="P1", price=25.00)
    p2 = await _create_product(client, auth_headers, name_es="P2", name_en="P2", price=18.00)

    sale = await _create_sale(
        client,
        auth_headers,
        [
            {"product_id": p1["id"], "quantity": 2},
            {"product_id": p2["id"], "quantity": 1},
        ],
    )

    assert len(sale["items"]) == 2
    assert sale["total"] == "68.00"


@pytest.mark.asyncio
async def test_create_sale_snapshots_product_data(client: AsyncClient, auth_headers: dict):
    product = await _create_product(client, auth_headers, price=20.00)
    sale = await _create_sale(client, auth_headers, [{"product_id": product["id"], "quantity": 1}])

    # Update the product price
    await client.put(
        f"/api/v1/admin/products/{product['id']}",
        json={"price": 99.00},
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/admin/sales", headers=auth_headers)
    listed_sale = next(s for s in resp.json()["items"] if s["id"] == sale["id"])
    assert listed_sale["items"][0]["price"] == "20.00"


@pytest.mark.asyncio
async def test_create_sale_product_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/admin/sales",
        json={"payment_method": "Efectivo", "items": [{"product_id": 99999, "quantity": 1}]},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_sale_invalid_payment_method(client: AsyncClient, auth_headers: dict):
    product = await _create_product(client, auth_headers)
    resp = await client.post(
        "/api/v1/admin/sales",
        json={"payment_method": "BitcoinXYZ", "items": [{"product_id": product["id"], "quantity": 1}]},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_sale_empty_items(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/admin/sales",
        json={"payment_method": "Efectivo", "items": []},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_sale_duplicate_product_id(client: AsyncClient, auth_headers: dict):
    product = await _create_product(client, auth_headers)
    resp = await client.post(
        "/api/v1/admin/sales",
        json={
            "payment_method": "Efectivo",
            "items": [
                {"product_id": product["id"], "quantity": 1},
                {"product_id": product["id"], "quantity": 2},
            ],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_sale_quantity_zero(client: AsyncClient, auth_headers: dict):
    product = await _create_product(client, auth_headers)
    resp = await client.post(
        "/api/v1/admin/sales",
        json={"payment_method": "Efectivo", "items": [{"product_id": product["id"], "quantity": 0}]},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_sale_item_no_category(client: AsyncClient, auth_headers: dict):
    product = await _create_product(client, auth_headers)
    sale = await _create_sale(client, auth_headers, [{"product_id": product["id"], "quantity": 1}])

    item = sale["items"][0]
    assert item["category_id"] is None
    assert item["category_name_es"] is None
    assert item["category_name_en"] is None


@pytest.mark.asyncio
async def test_create_sale_subtotal_computed(client: AsyncClient, auth_headers: dict):
    product = await _create_product(client, auth_headers, price=25.00)
    sale = await _create_sale(client, auth_headers, [{"product_id": product["id"], "quantity": 3}])

    assert sale["items"][0]["subtotal"] == "75.00"


@pytest.mark.asyncio
async def test_create_sale_total_is_sum_of_subtotals(client: AsyncClient, auth_headers: dict):
    p1 = await _create_product(client, auth_headers, name_es="A", name_en="A", price=10.00)
    p2 = await _create_product(client, auth_headers, name_es="B", name_en="B", price=15.00)

    sale = await _create_sale(
        client,
        auth_headers,
        [
            {"product_id": p1["id"], "quantity": 3},
            {"product_id": p2["id"], "quantity": 2},
        ],
    )

    subtotals = sum(float(item["subtotal"]) for item in sale["items"])
    assert float(sale["total"]) == subtotals


# ── List sales ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_sales_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/admin/sales", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_sales_all(client: AsyncClient, auth_headers: dict):
    p = await _create_product(client, auth_headers)
    for _ in range(3):
        await _create_sale(client, auth_headers, [{"product_id": p["id"], "quantity": 1}])

    resp = await client.get("/api/v1/admin/sales", headers=auth_headers)
    assert resp.json()["total"] == 3
    for sale in resp.json()["items"]:
        assert "items" in sale


@pytest.mark.asyncio
async def test_list_sales_order_asc(client: AsyncClient, auth_headers: dict):
    p = await _create_product(client, auth_headers)
    ids = []
    for _ in range(3):
        s = await _create_sale(client, auth_headers, [{"product_id": p["id"], "quantity": 1}])
        ids.append(s["id"])

    resp = await client.get("/api/v1/admin/sales?order=asc", headers=auth_headers)
    returned_ids = [s["id"] for s in resp.json()["items"]]
    assert returned_ids == sorted(returned_ids)


@pytest.mark.asyncio
async def test_list_sales_filter_by_product_id(client: AsyncClient, auth_headers: dict):
    p1 = await _create_product(client, auth_headers, name_es="P1", name_en="P1")
    p2 = await _create_product(client, auth_headers, name_es="P2", name_en="P2")
    await _create_sale(client, auth_headers, [{"product_id": p1["id"], "quantity": 1}])
    await _create_sale(client, auth_headers, [{"product_id": p2["id"], "quantity": 1}])

    resp = await client.get(f"/api/v1/admin/sales?product_id={p1['id']}", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["items"][0]["product_id"] == p1["id"]


@pytest.mark.asyncio
async def test_list_sales_filter_by_product_id_multi_item_sale(client: AsyncClient, auth_headers: dict):
    p1 = await _create_product(client, auth_headers, name_es="P1", name_en="P1")
    p2 = await _create_product(client, auth_headers, name_es="P2", name_en="P2")
    await _create_sale(
        client,
        auth_headers,
        [{"product_id": p1["id"], "quantity": 1}, {"product_id": p2["id"], "quantity": 1}],
    )

    resp = await client.get(f"/api/v1/admin/sales?product_id={p1['id']}", headers=auth_headers)
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_list_sales_filter_by_category_id(client: AsyncClient, auth_headers: dict):
    cat = await _create_category(client, auth_headers, name_es="Cestas", name_en="Baskets")
    p_with_cat = await _create_product(client, auth_headers, category_id=cat["id"])
    p_no_cat = await _create_product(client, auth_headers, name_es="NoCat", name_en="NoCat")

    await _create_sale(client, auth_headers, [{"product_id": p_with_cat["id"], "quantity": 1}])
    await _create_sale(client, auth_headers, [{"product_id": p_no_cat["id"], "quantity": 1}])

    resp = await client.get(f"/api/v1/admin/sales?category_id={cat['id']}", headers=auth_headers)
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["items"][0]["category_id"] == cat["id"]


@pytest.mark.asyncio
async def test_list_sales_filter_by_payment_method(client: AsyncClient, auth_headers: dict):
    p = await _create_product(client, auth_headers)
    await _create_sale(client, auth_headers, [{"product_id": p["id"], "quantity": 1}], payment_method="Efectivo")
    await _create_sale(client, auth_headers, [{"product_id": p["id"], "quantity": 1}], payment_method="Transferencia")

    resp = await client.get("/api/v1/admin/sales?payment_method=Efectivo", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["payment_method"] == "Efectivo"


@pytest.mark.asyncio
async def test_list_sales_filter_by_date_range(client: AsyncClient, auth_headers: dict):
    p = await _create_product(client, auth_headers)
    await _create_sale(client, auth_headers, [{"product_id": p["id"], "quantity": 1}])

    # Far-future date_from excludes the sale
    resp = await client.get("/api/v1/admin/sales?date_from=2099-01-01T00:00:00Z", headers=auth_headers)
    assert resp.json()["total"] == 0

    # Far-past date_to excludes the sale
    resp = await client.get("/api/v1/admin/sales?date_to=2000-01-01T00:00:00Z", headers=auth_headers)
    assert resp.json()["total"] == 0

    # No filter includes it
    resp = await client.get("/api/v1/admin/sales", headers=auth_headers)
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_list_sales_filter_by_total_range(client: AsyncClient, auth_headers: dict):
    p = await _create_product(client, auth_headers, price=10.00)
    await _create_sale(client, auth_headers, [{"product_id": p["id"], "quantity": 1}])   # total=10
    await _create_sale(client, auth_headers, [{"product_id": p["id"], "quantity": 5}])   # total=50

    resp = await client.get("/api/v1/admin/sales?total_max=20", headers=auth_headers)
    assert resp.json()["total"] == 1
    assert float(resp.json()["items"][0]["total"]) <= 20

    resp = await client.get("/api/v1/admin/sales?total_min=30", headers=auth_headers)
    assert resp.json()["total"] == 1
    assert float(resp.json()["items"][0]["total"]) >= 30


@pytest.mark.asyncio
async def test_list_sales_combined_filters(client: AsyncClient, auth_headers: dict):
    p1 = await _create_product(client, auth_headers, name_es="P1", name_en="P1", price=10.00)
    p2 = await _create_product(client, auth_headers, name_es="P2", name_en="P2", price=10.00)

    await _create_sale(client, auth_headers, [{"product_id": p1["id"], "quantity": 1}], payment_method="Efectivo")
    await _create_sale(client, auth_headers, [{"product_id": p2["id"], "quantity": 1}], payment_method="Efectivo")
    await _create_sale(client, auth_headers, [{"product_id": p1["id"], "quantity": 1}], payment_method="Transferencia")

    resp = await client.get(
        f"/api/v1/admin/sales?product_id={p1['id']}&payment_method=Efectivo",
        headers=auth_headers,
    )
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_list_sales_pagination(client: AsyncClient, auth_headers: dict):
    p = await _create_product(client, auth_headers)
    for _ in range(25):
        await _create_sale(client, auth_headers, [{"product_id": p["id"], "quantity": 1}])

    resp = await client.get("/api/v1/admin/sales?page=1&per_page=20", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 25
    assert data["pages"] == 2
    assert len(data["items"]) == 20

    resp2 = await client.get("/api/v1/admin/sales?page=2&per_page=20", headers=auth_headers)
    assert len(resp2.json()["items"]) == 5


# ── Payment methods in settings ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_settings_payment_methods_in_response(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/admin/settings", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "payment_methods" in data
    assert isinstance(data["payment_methods"], list)


@pytest.mark.asyncio
async def test_update_payment_methods(client: AsyncClient, auth_headers: dict):
    resp = await client.put(
        "/api/v1/admin/settings",
        json={"payment_methods": ["Efectivo", "Transferencia"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["payment_methods"] == ["Efectivo", "Transferencia"]

    resp2 = await client.get("/api/v1/admin/settings", headers=auth_headers)
    assert resp2.json()["payment_methods"] == ["Efectivo", "Transferencia"]


@pytest.mark.asyncio
async def test_update_payment_methods_duplicates_rejected(client: AsyncClient, auth_headers: dict):
    resp = await client.put(
        "/api/v1/admin/settings",
        json={"payment_methods": ["Efectivo", "Efectivo"]},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_payment_methods_empty_string_rejected(client: AsyncClient, auth_headers: dict):
    resp = await client.put(
        "/api/v1/admin/settings",
        json={"payment_methods": [""]},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sale_payment_method_validates_against_settings(client: AsyncClient, auth_headers: dict):
    await client.put(
        "/api/v1/admin/settings",
        json={"payment_methods": ["Efectivo"]},
        headers=auth_headers,
    )
    product = await _create_product(client, auth_headers)
    resp = await client.post(
        "/api/v1/admin/sales",
        json={"payment_method": "Transferencia", "items": [{"product_id": product["id"], "quantity": 1}]},
        headers=auth_headers,
    )
    assert resp.status_code == 400


# ── Product deletion does not break sale history ───────────────────────────────

@pytest.mark.asyncio
async def test_sale_survives_product_deletion(client: AsyncClient, auth_headers: dict):
    p1 = await _create_product(client, auth_headers, name_es="P1", name_en="P1")
    p2 = await _create_product(client, auth_headers, name_es="P2", name_en="P2")

    sale = await _create_sale(
        client,
        auth_headers,
        [{"product_id": p1["id"], "quantity": 1}, {"product_id": p2["id"], "quantity": 1}],
    )

    await client.delete(f"/api/v1/admin/products/{p1['id']}", headers=auth_headers)

    resp = await client.get("/api/v1/admin/sales", headers=auth_headers)
    listed = next(s for s in resp.json()["items"] if s["id"] == sale["id"])

    assert listed is not None
    deleted_item = next(i for i in listed["items"] if i["product_name_es"] == "P1")
    assert deleted_item["product_id"] is None
    assert deleted_item["product_name_es"] == "P1"
