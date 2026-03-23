# LUPE Backend

FastAPI backend for the LUPE handmade crafts catalog.

## Quick Start (Docker)

```bash
cp .env.example .env
# Edit .env — set SECRET_KEY, DB_PASSWORD, STORAGE_ACCESS_KEY, STORAGE_SECRET_KEY, WHATSAPP_NUMBER
docker compose up --build
```

API available at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.
MinIO console available at `http://localhost:9001`.

## Local Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start PostgreSQL and MinIO
docker compose up db minio -d

# Copy and edit env
cp .env.example .env
# Set DATABASE_URL to point to localhost: postgresql+asyncpg://lupe:secret@localhost:5432/lupe
# Set STORAGE_ENDPOINT=http://localhost:9000 (API reaches MinIO directly when running outside Docker)

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

## Image Storage

Images are stored in MinIO (S3-compatible object storage) instead of the local filesystem.

- The DB stores the storage key (e.g. `products/15/img_abc.jpg`)
- API responses include the full public URL: `{STORAGE_PUBLIC_URL}/{STORAGE_BUCKET}/{key}`
- Dev: `http://localhost:9000/lupe-media/{key}`
- Prod: set `STORAGE_PUBLIC_URL` to your VM's IP (e.g. `http://YOUR_VM_IP:9000`)
