# 001 — LUPE Image Manager: MinIO Image Storage

**Version 1.0 — March 2026**
**Depends on: `000_LUPE_Backend_Spec.md`**

---

## 1. Goal

Replace local-disk image storage with MinIO, an S3-compatible object storage server that runs as a Docker container. Same setup for both development and production (VM).

---

## 2. How It Works

- MinIO runs as a Docker service alongside `db` and `api`.
- Images are uploaded to a MinIO bucket instead of the local filesystem.
- The DB stores only the storage key (e.g. `products/15/img_abc.jpg`) — unchanged from the current schema.
- The full public URL is constructed as `{STORAGE_PUBLIC_URL}/{STORAGE_BUCKET}/{key}`.

---

## 3. New Environment Variables

Remove `MEDIA_DIR`. Add to `.env.example` and `app/config.py`:

| Variable | Dev value | Production (VM) value |
|---|---|---|
| `STORAGE_ENDPOINT` | `http://minio:9000` | `http://minio:9000` |
| `STORAGE_PUBLIC_URL` | `http://localhost:9000` | `http://YOUR_VM_IP:9000` |
| `STORAGE_ACCESS_KEY` | `minioadmin` | choose a strong value |
| `STORAGE_SECRET_KEY` | `minioadmin` | choose a strong value |
| `STORAGE_BUCKET` | `lupe-media` | `lupe-media` |

`STORAGE_ENDPOINT` is used by the `api` container to upload (internal Docker network). `STORAGE_PUBLIC_URL` is used to build image URLs returned to the browser.

Add a helper to `app/config.py`:

```python
def image_url(self, key: str) -> str:
    return f"{self.STORAGE_PUBLIC_URL}/{self.STORAGE_BUCKET}/{key}"
```

---

## 4. New File: `app/services/storage_service.py`

```python
from miniopy_async import Minio
from app.config import settings

# Strip the scheme from the endpoint — miniopy-async takes host:port only
def _endpoint() -> str:
    return settings.STORAGE_ENDPOINT.replace("http://", "").replace("https://", "")

def _client() -> Minio:
    return Minio(
        _endpoint(),
        access_key=settings.STORAGE_ACCESS_KEY,
        secret_key=settings.STORAGE_SECRET_KEY,
        secure=False,  # set True in production if using HTTPS
    )


async def ensure_bucket() -> None:
    """Create bucket and set public-read policy. Called once on startup."""
    client = _client()
    exists = await client.bucket_exists(settings.STORAGE_BUCKET)
    if not exists:
        await client.make_bucket(settings.STORAGE_BUCKET)

    # MinIO requires this policy format to allow public read on objects.
    # The syntax looks AWS-like because MinIO adopted the same policy standard.
    policy = f"""{{
        "Version": "2012-10-17",
        "Statement": [{{
            "Effect": "Allow",
            "Principal": "*",
            "Action": ["s3:GetObject"],
            "Resource": ["arn:aws:s3:::{settings.STORAGE_BUCKET}/*"]
        }}]
    }}"""
    await client.set_bucket_policy(settings.STORAGE_BUCKET, policy)


async def upload(key: str, data: bytes) -> None:
    import io
    client = _client()
    await client.put_object(
        settings.STORAGE_BUCKET,
        key,
        io.BytesIO(data),
        length=len(data),
        content_type="image/jpeg",
    )


async def delete(key: str) -> None:
    client = _client()
    await client.remove_object(settings.STORAGE_BUCKET, key)
```

---

## 5. `app/services/image_service.py` — Full Rewrite

Same validation and processing logic. Only the save/delete I/O changes.

```python
import io
import uuid
from fastapi import UploadFile, HTTPException, status
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.product_image import ProductImage
from app.models.product import Product
from app.services import storage_service
from app.config import settings

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024


async def upload_images(
    db: AsyncSession, product: Product, files: list[UploadFile], username: str = "admin"
) -> list[ProductImage]:
    next_order = len(product.images)
    created_images: list[ProductImage] = []

    for file in files:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{file.filename}' has unsupported type '{file.content_type}'. Allowed: JPEG, PNG, WebP",
            )

        contents = await file.read()
        if len(contents) > MAX_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File '{file.filename}' exceeds maximum size of {settings.MAX_IMAGE_SIZE_MB}MB",
            )

        img = Image.open(io.BytesIO(contents))
        if img.mode == "RGBA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        if img.width > settings.IMAGE_MAX_WIDTH:
            ratio = settings.IMAGE_MAX_WIDTH / img.width
            img = img.resize((settings.IMAGE_MAX_WIDTH, int(img.height * ratio)), Image.LANCZOS)

        output = io.BytesIO()
        img.save(output, format="JPEG", quality=settings.IMAGE_QUALITY, optimize=True)

        key = f"products/{product.id}/img_{uuid.uuid4().hex}.jpg"
        await storage_service.upload(key, output.getvalue())

        product_image = ProductImage(
            product_id=product.id,
            image_path=key,
            sort_order=next_order,
        )
        db.add(product_image)
        await db.flush()
        await db.refresh(product_image)
        created_images.append(product_image)
        next_order += 1

    await db.refresh(product)
    return created_images


async def delete_image(db: AsyncSession, image_id: int) -> Product:
    result = await db.execute(select(ProductImage).where(ProductImage.id == image_id))
    image = result.scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    await storage_service.delete(image.image_path)

    product_id = image.product_id
    await db.delete(image)
    await db.flush()

    product_result = await db.execute(select(Product).where(Product.id == product_id))
    product = product_result.scalar_one()
    await db.refresh(product)
    return product
```

---

## 6. `app/main.py` — Lifespan Change

```python
from app.services import storage_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    await storage_service.ensure_bucket()
    yield
```

Remove the `StaticFiles` mount and `media_path.mkdir(...)` block from `create_app`.

---

## 7. Response Schema Change

Add `image_url` to `ProductImageResponse` in `app/schemas/product.py`:

```python
class ProductImageResponse(BaseModel):
    id: int
    image_path: str   # storage key
    image_url: str    # full public URL
    sort_order: int
```

In the router helpers (`admin.py` and `public.py`), update image serialization:

```python
# When building images list:
images=[
    ProductImageResponse(
        id=img.id,
        image_path=img.image_path,
        image_url=settings.image_url(img.image_path),
        sort_order=img.sort_order,
    )
    for img in product.images
]

# When building primary_image in list responses:
primary_image=settings.image_url(product.images[0].image_path) if product.images else None
```

---

## 8. `docker-compose.yml` Changes

Add `minio` service. Remove `media_data` volume.

```yaml
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${STORAGE_ACCESS_KEY:-minioadmin}
      MINIO_ROOT_PASSWORD: ${STORAGE_SECRET_KEY:-minioadmin}
    ports:
      - "9000:9000"   # MinIO API
      - "9001:9001"   # Web console
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    depends_on:
      db:
        condition: service_started
      minio:
        condition: service_healthy
```

Add `minio_data` to the `volumes` section. Remove `media_data`.

---

## 9. Dependencies

Add to `requirements.txt`:
```
miniopy-async>=1.20
```

---

## 10. Tests

Mock storage in `tests/conftest.py` so tests don't need a running MinIO:

```python
from unittest.mock import AsyncMock
import pytest

@pytest.fixture(autouse=True)
def mock_storage(monkeypatch):
    monkeypatch.setattr("app.services.image_service.storage_service.upload", AsyncMock())
    monkeypatch.setattr("app.services.image_service.storage_service.delete", AsyncMock())
    monkeypatch.setattr("app.services.storage_service.ensure_bucket", AsyncMock())
```

---

## 11. No Migration Required

`product_images.image_path` stores the same string format (`products/15/img_abc.jpg`) — only the meaning changes from filesystem path to MinIO key.

---

## 12. Implementation Order

1. Add `miniopy-async` to `requirements.txt`.
2. Update `app/config.py` — remove `MEDIA_DIR`, add storage vars and `image_url()`.
3. Create `app/services/storage_service.py`.
4. Rewrite `app/services/image_service.py`.
5. Update `app/main.py` lifespan, remove `StaticFiles` mount.
6. Update `app/schemas/product.py` — add `image_url` field.
7. Update router helpers in `admin.py` and `public.py`.
8. Update `docker-compose.yml`.
9. Update `.env.example`.
10. Add `mock_storage` fixture to `tests/conftest.py`.
