from sqlalchemy import String, Integer, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from datetime import datetime
from sqlalchemy import func


class ProductHistory(Base):
    __tablename__ = "product_history"
    __table_args__ = (
        CheckConstraint("action IN ('created', 'updated', 'deleted')", name="ck_history_action"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    changed_by: Mapped[str] = mapped_column(String(50), nullable=False, server_default="admin")
    changed_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    product: Mapped["Product"] = relationship("Product", back_populates="history")
