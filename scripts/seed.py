"""
Seed script: creates initial admin user, store settings, and sample categories.
Idempotent — safe to run multiple times.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

from app.config import settings
from app.models.admin_user import AdminUser
from app.models.store_settings import StoreSettings
from app.models.category import Category
from app.utils.security import hash_password
from app.utils.slugify import generate_slug

SAMPLE_CATEGORIES = [
    {"name_es": "Cestas", "name_en": "Baskets"},
    {"name_es": "Cerámica", "name_en": "Ceramics"},
    {"name_es": "Textiles", "name_en": "Textiles"},
    {"name_es": "Joyería", "name_en": "Jewelry"},
    {"name_es": "Decoración", "name_en": "Decor"},
]


async def seed() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        # Admin user
        result = await db.execute(select(AdminUser).where(AdminUser.username == settings.ADMIN_DEFAULT_USERNAME))
        if result.scalar_one_or_none() is None:
            admin = AdminUser(
                username=settings.ADMIN_DEFAULT_USERNAME,
                password_hash=hash_password(settings.ADMIN_DEFAULT_PASSWORD),
            )
            db.add(admin)
            print(f"Created admin user: {settings.ADMIN_DEFAULT_USERNAME}")
        else:
            print(f"Admin user '{settings.ADMIN_DEFAULT_USERNAME}' already exists — skipping")

        # Store settings (id=1)
        result = await db.execute(select(StoreSettings).where(StoreSettings.id == 1))
        if result.scalar_one_or_none() is None:
            store = StoreSettings(
                id=1,
                store_name="LUPE",
                whatsapp_number=os.environ.get("WHATSAPP_NUMBER", "+5493534000000"),
                currency_symbol="$",
                default_language="es",
            )
            db.add(store)
            print("Created store settings")
        else:
            print("Store settings already exist — skipping")

        # Sample categories
        for cat_data in SAMPLE_CATEGORIES:
            slug = generate_slug(cat_data["name_en"])
            result = await db.execute(select(Category).where(Category.slug == slug))
            if result.scalar_one_or_none() is None:
                cat = Category(name_es=cat_data["name_es"], name_en=cat_data["name_en"], slug=slug)
                db.add(cat)
                print(f"Created category: {cat_data['name_en']}")
            else:
                print(f"Category '{cat_data['name_en']}' already exists — skipping")

        await db.commit()
        print("Seed complete.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
