import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy import delete

from app.main import app
from app.dependencies import get_db
from app.models.base import Base
from app.models import *  # noqa: F401, F403 — ensure all models are registered
from app.utils.security import hash_password
from app.models.admin_user import AdminUser
from app.models.store_settings import StoreSettings
from app.config import settings

TEST_DATABASE_URL = settings.DATABASE_URL.replace("/lupe", "/lupe_test")


@pytest_asyncio.fixture(scope="session")
async def engine():
    _engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield _engine
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Clean and seed admin + settings for each test
    await db_session.execute(delete(AdminUser))
    await db_session.execute(delete(StoreSettings))
    admin = AdminUser(username="admin", password_hash=hash_password("testpass123"))
    store = StoreSettings(
        id=1,
        store_name="LUPE",
        whatsapp_number="+5493534000000",
        currency_symbol="$",
        default_language="es",
    )
    db_session.add(admin)
    db_session.add(store)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_storage(monkeypatch):
    monkeypatch.setattr("app.services.image_service.storage_service.upload", AsyncMock())
    monkeypatch.setattr("app.services.image_service.storage_service.delete", AsyncMock())
    monkeypatch.setattr("app.services.storage_service.ensure_bucket", AsyncMock())


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/admin/login", json={"username": "admin", "password": "testpass123"}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def auth_headers(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}
