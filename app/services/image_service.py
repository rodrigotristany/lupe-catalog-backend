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
