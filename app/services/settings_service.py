from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.store_settings import StoreSettings
from app.schemas.settings import SettingsUpdate


async def get_settings(db: AsyncSession) -> StoreSettings:
    result = await db.execute(select(StoreSettings).where(StoreSettings.id == 1))
    settings = result.scalar_one_or_none()
    if settings is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store settings not configured")
    return settings


async def update_settings(db: AsyncSession, data: SettingsUpdate) -> StoreSettings:
    store_settings = await get_settings(db)
    if data.store_name is not None:
        store_settings.store_name = data.store_name
    if data.whatsapp_number is not None:
        store_settings.whatsapp_number = data.whatsapp_number
    if data.currency_symbol is not None:
        store_settings.currency_symbol = data.currency_symbol
    if data.default_language is not None:
        store_settings.default_language = data.default_language
    await db.flush()
    await db.refresh(store_settings)
    return store_settings
