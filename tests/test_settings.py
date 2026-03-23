import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_public_settings(client: AsyncClient):
    resp = await client.get("/api/v1/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["store_name"] == "LUPE"
    assert data["whatsapp_number"] == "+5493534000000"
    assert data["currency_symbol"] == "$"
    assert data["default_language"] == "es"


@pytest.mark.asyncio
async def test_get_admin_settings(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/admin/settings", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["store_name"] == "LUPE"


@pytest.mark.asyncio
async def test_update_settings(client: AsyncClient, auth_headers: dict):
    resp = await client.put(
        "/api/v1/admin/settings",
        json={"whatsapp_number": "+5491134567890", "currency_symbol": "ARS"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["whatsapp_number"] == "+5491134567890"
    assert data["currency_symbol"] == "ARS"


@pytest.mark.asyncio
async def test_update_settings_invalid_whatsapp(client: AsyncClient, auth_headers: dict):
    resp = await client.put(
        "/api/v1/admin/settings",
        json={"whatsapp_number": "12345"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_settings_invalid_language(client: AsyncClient, auth_headers: dict):
    resp = await client.put(
        "/api/v1/admin/settings",
        json={"default_language": "fr"},
        headers=auth_headers,
    )
    assert resp.status_code == 422
