from sqlalchemy import String, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
from datetime import datetime
from sqlalchemy import func


class StoreSettings(Base):
    __tablename__ = "store_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_name: Mapped[str] = mapped_column(String(100), nullable=False, server_default="LUPE")
    whatsapp_number: Mapped[str] = mapped_column(String(20), nullable=False)
    currency_symbol: Mapped[str] = mapped_column(String(5), nullable=False, server_default="$")
    default_language: Mapped[str] = mapped_column(String(2), nullable=False, server_default="es")
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
