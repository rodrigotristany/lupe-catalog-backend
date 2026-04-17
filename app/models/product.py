from decimal import Decimal
from sqlalchemy import String, Text, DECIMAL, Boolean, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (
        Index("idx_products_category_id", "category_id"),
        Index("idx_products_is_active", "is_active"),
        Index("idx_products_name_es", "name_es"),
        Index("idx_products_name_en", "name_en"),
        Index("idx_products_priority", "priority"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name_es: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    description_es: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    description_en: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    cover_image_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("product_images.id", ondelete="SET NULL", use_alter=True, name="fk_products_cover_image_id"),
        nullable=True,
    )

    category: Mapped["Category | None"] = relationship(
        "Category", back_populates="products", lazy="selectin"
    )
    images: Mapped[list["ProductImage"]] = relationship(
        "ProductImage",
        primaryjoin="Product.id == ProductImage.product_id",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.sort_order",
        lazy="selectin",
    )
    cover_image: Mapped["ProductImage | None"] = relationship(
        "ProductImage",
        primaryjoin="Product.cover_image_id == ProductImage.id",
        foreign_keys="[Product.cover_image_id]",
        lazy="selectin",
    )
    history: Mapped[list["ProductHistory"]] = relationship(
        "ProductHistory",
        back_populates="product",
        cascade="all, delete-orphan",
    )
