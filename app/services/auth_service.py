from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.admin_user import AdminUser
from app.utils.security import verify_password, create_token
from app.config import settings


async def authenticate_admin(db: AsyncSession, username: str, password: str) -> str | None:
    result = await db.execute(select(AdminUser).where(AdminUser.username == username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        return None
    return create_token(subject=username)
