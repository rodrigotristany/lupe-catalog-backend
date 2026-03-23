# LUPE Backend

FastAPI backend for the LUPE handmade crafts catalog.

## Quick Start (Docker)

```bash
cp .env.example .env
# Edit .env — set SECRET_KEY, DB_PASSWORD, WHATSAPP_NUMBER
docker compose up --build
```

API available at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

## Local Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start PostgreSQL (or use Docker for just the DB)
docker compose up db -d

# Copy and edit env
cp .env.example .env
# Set DATABASE_URL to point to localhost: postgresql+asyncpg://lupe:secret@localhost:5432/lupe

# Run migrations
alembic upgrade head

# Seed initial data
python scripts/seed.py

# Start dev server
uvicorn app.main:app --reload
```

## Environment Variables

See `.env.example` for all required variables.

## Running Tests

```bash
# Requires a running PostgreSQL instance named lupe_test
pytest
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/v1/admin/login | — | Get JWT token |
| GET | /api/v1/products | — | List active products |
| GET | /api/v1/products/{id} | — | Get product detail |
| GET | /api/v1/categories | — | List categories |
| GET | /api/v1/settings | — | Get store settings |
| GET | /api/v1/admin/products | JWT | List all products (incl. inactive) |
| POST | /api/v1/admin/products | JWT | Create product |
| PUT | /api/v1/admin/products/{id} | JWT | Update product |
| DELETE | /api/v1/admin/products/{id} | JWT | Soft-delete product |
| POST | /api/v1/admin/products/{id}/images | JWT | Upload images |
| DELETE | /api/v1/admin/images/{id} | JWT | Delete image |
| GET | /api/v1/admin/products/{id}/history | JWT | Product change history |
| POST | /api/v1/admin/categories | JWT | Create category |
| PUT | /api/v1/admin/categories/{id} | JWT | Update category |
| DELETE | /api/v1/admin/categories/{id} | JWT | Delete category |
| GET | /api/v1/admin/settings | JWT | Get settings (admin) |
| PUT | /api/v1/admin/settings | JWT | Update settings |

## Image Serving

- Dev: `http://localhost:8000/media/{image_path}`
- Prod: served by Nginx directly from the media volume
