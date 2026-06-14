from decimal import Decimal
from datetime import datetime
from sqlalchemy import String, Integer, DECIMAL, ForeignKey, Index, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (
        Index("idx_sales_created_at", "created_at"),
        Index("idx_sales_payment_method", "payment_method"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    payment_method: Mapped[str] = mapped_column(String(100), nullable=False)
    total: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    items: Mapped[list["SaleProduct"]] = relationship(
        "SaleProduct",
        back_populates="sale",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SaleProduct(Base):
    __tablename__ = "sales_products"
    __table_args__ = (
        Index("idx_sales_products_sale_id", "sale_id"),
        Index("idx_sales_products_product_id", "product_id"),
        Index("idx_sales_products_category_id", "category_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sales.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    product_name_es: Mapped[str] = mapped_column(String(255), nullable=False)
    product_name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category_name_es: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category_name_en: Mapped[str | None] = mapped_column(String(100), nullable=True)
    price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)

    sale: Mapped["Sale"] = relationship("Sale", back_populates="items")
