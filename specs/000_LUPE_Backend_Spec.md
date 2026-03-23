# LUPE — Backend & Database Technical Specification

**Version 1.0 — March 2026**
**Repository: `lupe-backend`**

---

## 1. Overview

This document specifies the backend API and database layer for the LUPE handmade crafts catalog. It is designed to be implementation-ready: an AI coding agent or developer should be able to build the entire backend from this document without ambiguity.

| Attribute | Value |
|---|---|
| Repository name | lupe-backend |
| Language | Python 3.12+ |
| Framework | FastAPI 0.115+ |
| ORM | SQLAlchemy 2.0+ (async) |
| Migrations | Alembic |
| Database | PostgreSQL 16 |
| Auth | JWT (PyJWT + passlib[bcrypt]) |
| Image handling | Pillow (resize/compress on upload) |
| Server | Uvicorn (dev) / Gunicorn + Uvicorn workers (prod) |
| Containerization | Docker + Docker Compose |
| Testing | pytest + httpx (async test client) |

---

## 2. Project Structure

The repository follows a modular layout. Each domain (products, categories, auth, settings) has its own router, schemas, and service module.

```
lupe-backend/
├── alembic/
│   ├── versions/           # Migration files
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI app factory, CORS, lifespan
│   ├── config.py           # Settings via pydantic-settings
│   ├── database.py         # Async engine, session factory
│   ├── dependencies.py     # Shared deps (get_db, get_current_admin)
│   ├── models/
│   │   ├── __init__.py     # Imports all models (for Alembic)
│   │   ├── base.py         # DeclarativeBase + mixins
│   │   ├── product.py
│   │   ├── category.py
│   │   ├── product_image.py
│   │   ├── product_history.py
│   │   ├── store_settings.py
│   │   └── admin_user.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── product.py      # Pydantic request/response schemas
│   │   ├── category.py
│   │   ├── auth.py
│   │   ├── settings.py
│   │   └── common.py       # Pagination, error schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── public.py       # /api/v1/products, /categories, /settings
│   │   └── admin.py        # /api/v1/admin/* (auth-protected)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── product_service.py
│   │   ├── category_service.py
│   │   ├── settings_service.py
│   │   ├── auth_service.py
│   │   └── image_service.py # Resize, compress, save to disk
│   └── utils/
│       ├── __init__.py
│       ├── security.py     # JWT encode/decode, password hashing
│       └── slugify.py      # Generate URL slugs
├── media/                  # Uploaded images (Docker volume)
├── tests/
│   ├── conftest.py         # Fixtures: test DB, client, admin token
│   ├── test_products.py
│   ├── test_categories.py
│   ├── test_auth.py
│   └── test_settings.py
├── scripts/
│   └── seed.py             # Seed DB with initial admin + sample data
├── alembic.ini
├── pyproject.toml
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 3. Environment Variables

All configuration is read from environment variables via pydantic-settings. A `.env.example` file must be provided in the repository root.

| Variable | Type | Example | Description |
|---|---|---|---|
| DATABASE_URL | str | `postgresql+asyncpg://lupe:secret@db:5432/lupe` | Async SQLAlchemy connection string |
| SECRET_KEY | str | `change-me-in-production-abc123` | JWT signing secret (min 32 chars) |
| JWT_ALGORITHM | str | `HS256` | JWT algorithm (fixed) |
| JWT_EXPIRATION_MINUTES | int | `1440` | Token TTL (default: 24 hours) |
| ADMIN_DEFAULT_USERNAME | str | `admin` | Seed script: initial admin username |
| ADMIN_DEFAULT_PASSWORD | str | `changeme123` | Seed script: initial admin password |
| MEDIA_DIR | str | `/app/media` | Absolute path for uploaded images |
| MAX_IMAGE_SIZE_MB | int | `5` | Max upload size per image in MB |
| IMAGE_MAX_WIDTH | int | `1200` | Resize images to max width in px |
| IMAGE_QUALITY | int | `85` | JPEG compression quality (1-100) |
| CORS_ORIGINS | str | `http://localhost:5173,https://lupe.example.com` | Comma-separated allowed origins |
| LOG_LEVEL | str | `INFO` | Python logging level |

---

## 4. Database Schema

All tables use snake_case naming. All primary keys are auto-incrementing integers. Timestamps use timezone-aware UTC. The schema is managed exclusively through Alembic migrations — never apply DDL manually.

### 4.1 categories

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | SERIAL | PK | Auto-increment primary key |
| name_es | VARCHAR(100) | NOT NULL | Category name in Spanish |
| name_en | VARCHAR(100) | NOT NULL | Category name in English |
| slug | VARCHAR(100) | NOT NULL, UNIQUE | URL-friendly identifier (auto-generated) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Last update timestamp |

### 4.2 products

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | SERIAL | PK | Auto-increment primary key |
| name_es | VARCHAR(255) | NOT NULL | Product name in Spanish |
| name_en | VARCHAR(255) | NOT NULL | Product name in English |
| description_es | TEXT | NOT NULL, DEFAULT '' | Description in Spanish |
| description_en | TEXT | NOT NULL, DEFAULT '' | Description in English |
| price | DECIMAL(10,2) | NOT NULL, CHECK(price >= 0) | Product price |
| category_id | INTEGER | FK → categories.id, ON DELETE SET NULL, NULLABLE | Category foreign key |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | Visibility toggle (soft delete) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Indexes:** `idx_products_category_id` on category_id; `idx_products_is_active` on is_active; `idx_products_name_es` for text search on name_es; `idx_products_name_en` for text search on name_en.

### 4.3 product_images

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | SERIAL | PK | Auto-increment primary key |
| product_id | INTEGER | FK → products.id, ON DELETE CASCADE, NOT NULL | Owning product |
| image_path | VARCHAR(500) | NOT NULL | Relative path from MEDIA_DIR (e.g., `products/15/img_001.jpg`) |
| sort_order | INTEGER | NOT NULL, DEFAULT 0 | Display order. 0 = primary/thumbnail image |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Upload timestamp |

### 4.4 product_history

Stores a full JSON snapshot of the product each time it is updated or deleted. This enables simple change tracking without complex diff logic.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | SERIAL | PK | Auto-increment primary key |
| product_id | INTEGER | FK → products.id, ON DELETE CASCADE, NOT NULL | The product that changed |
| action | VARCHAR(20) | NOT NULL, CHECK IN ('created','updated','deleted') | Type of change |
| snapshot | JSONB | NOT NULL | Full product state at time of change (all fields + image paths) |
| changed_by | VARCHAR(50) | NOT NULL, DEFAULT 'admin' | Username of who made the change |
| changed_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | When the change occurred |

The snapshot JSONB column stores the complete product data at the moment of change, including: name_es, name_en, description_es, description_en, price, category_id, is_active, and an array of image_paths. This approach is simple, queryable (PostgreSQL JSONB operators), and avoids the complexity of column-by-column diffing.

**Snapshot JSON structure:**

```json
{
  "name_es": "Canasta Tejida",
  "name_en": "Handwoven Basket",
  "description_es": "...",
  "description_en": "...",
  "price": "25.00",
  "category_id": 3,
  "is_active": true,
  "image_paths": ["products/15/img_001.jpg", "products/15/img_002.jpg"]
}
```

### 4.5 store_settings

Single-row table. The application must enforce that only one row exists (id = 1). The seed script creates this row.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | SERIAL | PK | Always 1 |
| store_name | VARCHAR(100) | NOT NULL, DEFAULT 'LUPE' | Display name |
| whatsapp_number | VARCHAR(20) | NOT NULL | With country code, e.g., +5493534000000 |
| currency_symbol | VARCHAR(5) | NOT NULL, DEFAULT '$' | Currency display symbol |
| default_language | VARCHAR(2) | NOT NULL, DEFAULT 'es' | es or en |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Last update |

### 4.6 admin_users

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | SERIAL | PK | Auto-increment primary key |
| username | VARCHAR(50) | NOT NULL, UNIQUE | Login username |
| password_hash | VARCHAR(255) | NOT NULL | Bcrypt hash |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Creation timestamp |

---

## 5. Alembic Configuration

Alembic is configured for async PostgreSQL via asyncpg. Migrations are auto-generated from SQLAlchemy models.

### 5.1 Setup Commands

```bash
# Initialize (already done in repo structure)
alembic init alembic

# Generate migration after model changes
alembic revision --autogenerate -m "description_of_change"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### 5.2 env.py Configuration

- Import all models from `app.models` (so Alembic detects them).
- Read DATABASE_URL from environment (replace `+asyncpg` with `+psycopg2` for Alembic's sync connection, or configure async migration runner).
- Set `target_metadata = Base.metadata`.
- The initial migration must create all 6 tables defined in Section 4.

### 5.3 Seed Script (scripts/seed.py)

Run after the first migration to populate initial data:

1. Create the admin user with ADMIN_DEFAULT_USERNAME / ADMIN_DEFAULT_PASSWORD (bcrypt hashed).
2. Create the store_settings row (id=1) with store_name='LUPE' and the WhatsApp number from env or a placeholder.
3. Optionally create 3–5 sample categories (e.g., Baskets, Ceramics, Textiles, Jewelry, Decor) in both languages.
4. The seed script must be idempotent — running it twice must not create duplicates (use INSERT ON CONFLICT DO NOTHING or check existence).

---

## 6. SQLAlchemy Model Patterns

All models inherit from a shared Base with a TimestampMixin. Use SQLAlchemy 2.0 Mapped annotation style.

### 6.1 Base and Mixin

```python
# app/models/base.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import func
from datetime import datetime

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

### 6.2 Relationship Rules

- Product → Category: many-to-one (product.category_id FK). Use `lazy='selectin'` for the relationship to avoid N+1.
- Product → ProductImage: one-to-many. Cascade `'all, delete-orphan'`. Order by sort_order.
- Product → ProductHistory: one-to-many. Cascade `'all, delete-orphan'`. Order by changed_at DESC.
- All relationships use `back_populates` (explicit, never backref).

### 6.3 History Snapshot Creation

The product_service module is responsible for creating history entries. Every create, update, and delete operation on a product must also insert a row into product_history with the full snapshot. This logic lives in the service layer, not in ORM events, to keep it explicit and testable.

```python
# In product_service.py (pseudo-code)
async def _save_snapshot(db, product, action, username='admin'):
    snapshot = {
        "name_es": product.name_es,
        "name_en": product.name_en,
        "description_es": product.description_es,
        "description_en": product.description_en,
        "price": str(product.price),
        "category_id": product.category_id,
        "is_active": product.is_active,
        "image_paths": [img.image_path for img in product.images],
    }
    history = ProductHistory(
        product_id=product.id,
        action=action,
        snapshot=snapshot,
        changed_by=username
    )
    db.add(history)
```

---

## 7. API Specification

Base path: `/api/v1`. All responses are JSON. All request bodies are JSON (except image uploads which use multipart/form-data). Dates are ISO 8601 UTC.

### 7.1 Authentication

#### POST /api/v1/admin/login

Authenticate admin and return a JWT token.

**Request body:**

```json
{
  "username": "admin",
  "password": "changeme123"
}
```

**Response 200:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1440
}
```

**Response 401:**

```json
{
  "detail": "Invalid credentials"
}
```

All admin endpoints require the header: `Authorization: Bearer <token>`. The `get_current_admin` dependency decodes the JWT, verifies it, and returns the admin user. If invalid or expired, it returns 401.

### 7.2 Public Endpoints

#### GET /api/v1/products

Returns paginated list of active products.

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| category | string | (none) | Filter by category slug |
| search | string | (none) | Search in name_es and name_en (case-insensitive ILIKE) |
| page | int | 1 | Page number (1-based) |
| per_page | int | 20 | Items per page (max 100) |
| sort | string | created_at | Sort field: created_at, price, name_es, name_en |
| order | string | desc | Sort direction: asc or desc |

**Response 200:**

```json
{
  "items": [
    {
      "id": 15,
      "name_es": "Canasta Tejida",
      "name_en": "Handwoven Basket",
      "description_es": "Canasta artesanal...",
      "description_en": "Handmade basket...",
      "price": "25.00",
      "category": { "id": 3, "name_es": "Cestas", "name_en": "Baskets", "slug": "baskets" },
      "primary_image": "products/15/img_001.jpg",
      "is_active": true,
      "created_at": "2026-03-20T14:30:00Z",
      "updated_at": "2026-03-21T09:15:00Z"
    }
  ],
  "total": 48,
  "page": 1,
  "per_page": 20,
  "pages": 3
}
```

#### GET /api/v1/products/{id}

Returns a single active product with all images.

**Response 200:**

```json
{
  "id": 15,
  "name_es": "Canasta Tejida",
  "name_en": "Handwoven Basket",
  "description_es": "Canasta artesanal tejida a mano...",
  "description_en": "Handmade woven basket crafted from...",
  "price": "25.00",
  "category": { "id": 3, "name_es": "Cestas", "name_en": "Baskets", "slug": "baskets" },
  "images": [
    { "id": 1, "image_path": "products/15/img_001.jpg", "sort_order": 0 },
    { "id": 2, "image_path": "products/15/img_002.jpg", "sort_order": 1 }
  ],
  "is_active": true,
  "created_at": "2026-03-20T14:30:00Z",
  "updated_at": "2026-03-21T09:15:00Z"
}
```

Response 404 if product does not exist or is_active = false.

#### GET /api/v1/categories

Returns all categories (no pagination needed for ~10–20 categories).

**Response 200:**

```json
[
  { "id": 1, "name_es": "Cerámica", "name_en": "Ceramics", "slug": "ceramics" },
  { "id": 2, "name_es": "Textiles", "name_en": "Textiles", "slug": "textiles" },
  { "id": 3, "name_es": "Cestas", "name_en": "Baskets", "slug": "baskets" }
]
```

#### GET /api/v1/settings

Returns public store settings.

**Response 200:**

```json
{
  "store_name": "LUPE",
  "whatsapp_number": "+5493534000000",
  "currency_symbol": "$",
  "default_language": "es"
}
```

### 7.3 Admin Product Endpoints

All admin endpoints are prefixed with `/api/v1/admin` and require a valid JWT in the Authorization header.

#### GET /api/v1/admin/products

Same as public GET /products but includes inactive products (is_active = false). Same query params.

#### POST /api/v1/admin/products

Create a new product. Triggers a product_history snapshot with action='created'.

**Request body (JSON):**

```json
{
  "name_es": "Taza de Barro",
  "name_en": "Clay Mug",
  "description_es": "Taza hecha a mano...",
  "description_en": "Handmade clay mug...",
  "price": 18.00,
  "category_id": 1,
  "is_active": true
}
```

**Response 201:** Full product object (same shape as GET /products/{id}, images will be empty).

**Validation rules:**

- name_es and name_en: required, 1–255 characters.
- price: required, must be >= 0, max 2 decimal places.
- category_id: optional (nullable), must reference existing category if provided.
- is_active: optional, defaults to true.

#### PUT /api/v1/admin/products/{id}

Update an existing product. All fields are optional (partial update). Triggers a product_history snapshot with action='updated' AFTER the update is applied (snapshot reflects the NEW state).

**Request body (JSON, partial):**

```json
{
  "price": 22.00,
  "is_active": false
}
```

**Response 200:** Full updated product object.

Response 404 if product not found.

#### DELETE /api/v1/admin/products/{id}

Soft-delete: sets is_active = false. Triggers a product_history snapshot with action='deleted'. Does NOT delete the database row or images.

**Response 200:**

```json
{ "detail": "Product deleted (soft)" }
```

Response 404 if product not found.

#### POST /api/v1/admin/products/{id}/images

Upload one or more images for a product. Uses multipart/form-data.

**Request:** multipart/form-data with field name `files` (multiple files allowed).

**Processing pipeline:**

1. Validate each file: must be JPEG, PNG, or WebP; max size MAX_IMAGE_SIZE_MB.
2. Resize if width > IMAGE_MAX_WIDTH (maintain aspect ratio).
3. Convert to JPEG and compress at IMAGE_QUALITY.
4. Save to `MEDIA_DIR/products/{product_id}/img_{uuid}.jpg`.
5. Create product_images rows with incrementing sort_order.
6. Create product_history snapshot with action='updated' (new images reflect in snapshot).

**Response 201:**

```json
[
  { "id": 5, "image_path": "products/15/img_a1b2c3.jpg", "sort_order": 0 },
  { "id": 6, "image_path": "products/15/img_d4e5f6.jpg", "sort_order": 1 }
]
```

#### DELETE /api/v1/admin/images/{id}

Delete a single product image. Removes DB row AND file from disk. Triggers product_history snapshot with action='updated' on the parent product.

**Response 200:**

```json
{ "detail": "Image deleted" }
```

### 7.4 Admin Category Endpoints

#### POST /api/v1/admin/categories

**Request body:**

```json
{
  "name_es": "Joyería",
  "name_en": "Jewelry"
}
```

The slug is auto-generated from name_en (lowercase, hyphens, no special chars). Response 201 with the full category object.

#### PUT /api/v1/admin/categories/{id}

Partial update. Slug is regenerated if name_en changes. Response 200.

#### DELETE /api/v1/admin/categories/{id}

Hard delete. Products in this category will have category_id set to NULL (ON DELETE SET NULL). Response 200.

### 7.5 Admin Settings Endpoints

#### GET /api/v1/admin/settings

Returns full settings (same as public, but in admin context for the settings form).

#### PUT /api/v1/admin/settings

**Request body (partial update):**

```json
{
  "whatsapp_number": "+5493534999999",
  "currency_symbol": "ARS"
}
```

**Validation:**

- whatsapp_number: must match regex `^\+[0-9]{7,15}$` (international format with country code).
- currency_symbol: max 5 characters.
- default_language: must be 'es' or 'en'.

### 7.6 Admin Product History Endpoint

#### GET /api/v1/admin/products/{id}/history

Returns the change history for a specific product, ordered newest first.

**Response 200:**

```json
[
  {
    "id": 45,
    "action": "updated",
    "snapshot": { "name_es": "...", "price": "22.00", "..." : "..." },
    "changed_by": "admin",
    "changed_at": "2026-03-21T09:15:00Z"
  },
  {
    "id": 12,
    "action": "created",
    "snapshot": { "name_es": "...", "price": "18.00", "..." : "..." },
    "changed_by": "admin",
    "changed_at": "2026-03-20T14:30:00Z"
  }
]
```

---

## 8. Image Serving

Images are served directly by Nginx in production (not by FastAPI). The frontend constructs image URLs as:

```
{API_BASE_URL}/media/{image_path}

Example:
https://lupe.example.com/media/products/15/img_a1b2c3.jpg
```

In development (Docker Compose), FastAPI serves media files using StaticFiles mount at `/media` pointing to MEDIA_DIR. In production, Nginx serves the `/media` location directly from the media volume.

---

## 9. Error Handling

All errors return a consistent JSON structure:

```json
{
  "detail": "Human-readable error message"
}
```

| Status | When |
|---|---|
| 400 | Validation error, bad request body or params |
| 401 | Missing, invalid, or expired JWT token |
| 404 | Resource not found |
| 409 | Conflict (e.g., duplicate slug) |
| 413 | Image file too large |
| 422 | Pydantic validation failure (auto from FastAPI) |
| 500 | Unexpected server error |

FastAPI's built-in 422 response is fine for validation errors. For 400/401/404/409/413, use HTTPException with the detail message. Register a global exception handler for 500 that logs the full traceback and returns a generic message.

---

## 10. CORS Configuration

CORS is configured in main.py using FastAPI's CORSMiddleware:

- allow_origins: parsed from CORS_ORIGINS env var (comma-separated list).
- allow_methods: `['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']`.
- allow_headers: `['Content-Type', 'Authorization']`.
- allow_credentials: true.

---

## 11. Docker Configuration

### 11.1 Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 11.2 docker-compose.yml

```yaml
version: '3.9'
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: lupe
      POSTGRES_PASSWORD: ${DB_PASSWORD:-secret}
      POSTGRES_DB: lupe
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  api:
    build: .
    env_file: .env
    depends_on:
      - db
    volumes:
      - media_data:/app/media
    ports:
      - "8000:8000"
    command: >
      sh -c "alembic upgrade head &&
             python scripts/seed.py &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000"

volumes:
  postgres_data:
  media_data:
```

---

## 12. Testing Strategy

- Framework: pytest with pytest-asyncio and httpx.AsyncClient.
- Test database: Use a separate test database (lupe_test). Create/drop tables per test session.
- Fixtures in conftest.py: `async_client` (httpx client against the FastAPI app), `db_session` (fresh async session), `admin_token` (pre-authenticated JWT for admin tests).
- Test coverage target: 80%+ on service and router layers.

**Test categories:**

| File | Tests |
|---|---|
| test_auth.py | Login success, login invalid creds, access protected route without token, expired token |
| test_products.py | List products (public, filtered, searched, paginated), get single product, create (valid + invalid), update (partial), soft-delete, verify history snapshots created |
| test_categories.py | List categories, create, update (slug regeneration), delete (verify product FK set to null) |
| test_settings.py | Get settings, update (valid), update with invalid whatsapp format |
| test_images.py | Upload single image, upload multiple, delete image, upload invalid format, upload oversized file |

---

## 13. Python Dependencies

requirements.txt (pinned major.minor, allow patch updates):

| Package | Version | Purpose |
|---|---|---|
| fastapi | >=0.115,<1.0 | Web framework |
| uvicorn[standard] | >=0.30 | ASGI server |
| sqlalchemy[asyncio] | >=2.0,<3.0 | ORM (async mode) |
| asyncpg | >=0.29 | PostgreSQL async driver |
| alembic | >=1.13 | Database migrations |
| pydantic-settings | >=2.0 | Env var configuration |
| pyjwt | >=2.8 | JWT encode/decode |
| passlib[bcrypt] | >=1.7 | Password hashing |
| python-multipart | >=0.0.9 | File upload parsing |
| pillow | >=10.0 | Image processing |
| python-slugify | >=8.0 | Slug generation |
| pytest | >=8.0 | Testing (dev) |
| pytest-asyncio | >=0.23 | Async test support (dev) |
| httpx | >=0.27 | Async test client (dev) |

---

## 14. Implementation Checklist

An AI agent or developer should implement in this order:

1. Scaffold project structure (all folders and `__init__.py` files as defined in Section 2).
2. Create `config.py` with pydantic-settings reading all env vars from Section 3.
3. Create `database.py` with async engine and session factory.
4. Create all SQLAlchemy models (Section 4 and Section 6).
5. Initialize Alembic configuration and generate the initial migration.
6. Create `docker-compose.yml` and `Dockerfile` (Section 11). Verify DB starts and migration runs.
7. Implement `auth_service.py` and `security.py` (password hashing + JWT).
8. Implement the POST /admin/login endpoint. Test manually.
9. Implement `dependencies.py` (get_db, get_current_admin).
10. Implement `category_service.py` and category endpoints (CRUD). Write tests.
11. Implement `product_service.py` with history snapshot logic. Write tests.
12. Implement product CRUD endpoints (public + admin). Write tests.
13. Implement `image_service.py` (resize, compress, save). Write tests.
14. Implement image upload and delete endpoints. Write tests.
15. Implement `settings_service.py` and settings endpoints. Write tests.
16. Implement the product history endpoint. Write tests.
17. Create `seed.py` script. Verify with `docker-compose up`.
18. Add CORS middleware configuration.
19. Run full test suite and verify 80%+ coverage.
20. Write `README.md` with setup instructions.

---

## 15. Notes for AI Coding Agents

- Every decision has been made — do not introduce new libraries or patterns not specified here.
- Use async/await everywhere (async def for all route handlers, service functions, and DB operations).
- Use SQLAlchemy 2.0 style (`Mapped[]`, `mapped_column`) — do not use legacy 1.x `Column()` style.
- Every product create/update/delete MUST create a product_history snapshot. If tests don't verify this, they're incomplete.
- Image paths in the DB are always relative to MEDIA_DIR (e.g., `'products/15/img_abc.jpg'`), never absolute.
- The seed script is the only place where default data is created — do not put seed logic in migrations.
- Never hardcode the WhatsApp number, currency, or store name — always read from the store_settings table.
- All string validations (min/max length) must be enforced in Pydantic schemas, not just at the DB level.
- Return 404 for inactive products on public endpoints (don't leak that they exist).
- Price is stored as DECIMAL(10,2) in the DB and serialized as a string in JSON responses to avoid floating-point issues.
