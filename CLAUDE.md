# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the dev server
uvicorn app.main:app --reload

# Run all tests
pytest

# Run a single test file
pytest tests/test_products.py

# Run a single test by name
pytest tests/test_products.py::test_create_product

# Apply migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Seed the database
python scripts/seed.py
```

Tests require a `lupe_test` PostgreSQL database. The test suite derives the URL by replacing `/lupe` with `/lupe_test` in `DATABASE_URL` from `.env`.

## Architecture

**FastAPI + SQLAlchemy async** application. Everything is async end-to-end (asyncpg driver, `AsyncSession`, `pytest-asyncio`).

### Layer structure

```
app/
  main.py          # App factory (create_app), mounts routers and /media static files
  config.py        # Pydantic Settings — reads from .env
  database.py      # AsyncEngine + AsyncSessionLocal
  dependencies.py  # get_db (session per request, auto-commit/rollback), get_current_admin (JWT bearer)
  models/          # SQLAlchemy ORM models (Base + TimestampMixin in base.py)
  schemas/         # Pydantic request/response models
  services/        # Business logic — all DB queries live here, not in routers
  routers/
    public.py      # /api/v1/* — unauthenticated catalog endpoints
    admin.py       # /api/v1/admin/* — JWT-protected CRUD endpoints
```

### Key design decisions

- **Two router prefixes**: public (`/api/v1`) and admin (`/api/v1/admin`). Admin routes depend on `get_current_admin` which decodes a JWT bearer token.
- **Session lifecycle**: `get_db` commits on success and rolls back on exception. Services call `db.flush()` + `db.refresh()` mid-transaction rather than committing themselves.
- **Product deletion is soft**: sets `is_active=False`. The `include_inactive` flag controls visibility across public vs admin queries.
- **Product history**: every create/update/soft-delete writes a JSON snapshot to `product_history`. Image uploads also trigger a snapshot via `product_service._save_snapshot`.
- **Relationships use `lazy="selectin"`**: `Product.images` and `Product.category` are always eagerly loaded; no explicit `.options()` needed in queries.
- **Images**: stored on disk under `MEDIA_DIR`, served as static files at `/media`. `image_service` handles upload, resize (max width + quality), and deletion.
- **Bilingual content**: all product text fields exist in both `_es` and `_en` variants.

### Testing conventions

Tests use a real `lupe_test` database (no mocks). The `conftest.py` fixtures:
- `engine` (session-scoped): drops and recreates all tables once per test session.
- `db_session` (function-scoped): rolls back after each test.
- `client`: overrides `get_db`, seeds a default admin user and `StoreSettings`, returns an `AsyncClient`.
- `admin_token` / `auth_headers`: hit the real login endpoint and return the token/headers.
